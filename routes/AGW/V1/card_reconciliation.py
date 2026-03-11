import calendar
import io
import random
import re
from datetime import datetime

from flask import request
from flask_classful import route

from configs.customer_connection import get_conn
from functions.responses import set_response
from routes.v2.master import MasterView

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


class AGWCardReconciliationView(MasterView):

    @route('/analyze-pdfs', methods=['POST'])
    def analyze_pdfs(self):
        files = request.files.getlist('files')
        if not files:
            files = request.files.getlist('files[]')
        if not files:
            files = [value for key, value in request.files.items() if key.startswith('files[')]
        bank_hint = (request.form.get('bank_hint') or 'auto').strip().lower()

        if not files:
            return set_response([], 404, 'Debe adjuntar al menos un PDF.')

        parsed_files = []
        period_from_values = []
        period_to_values = []
        detected_brands = []
        detected_banks = []

        for item in files:
            filename = (item.filename or '').strip()
            extracted_text = self._extract_pdf_text(item)
            combined_text = f'{filename}\n{extracted_text}'

            brand = self._detect_brand(combined_text)
            bank = self._detect_bank(combined_text, bank_hint)
            period = self._detect_period(combined_text, filename)

            if brand != 'No detectada':
                detected_brands.append(brand)
            if bank != 'No detectado':
                detected_banks.append(bank)
            if period.get('from'):
                period_from_values.append(period['from'])
            if period.get('to'):
                period_to_values.append(period['to'])

            parsed_files.append({
                'name': filename,
                'size': item.content_length or 0,
                'detected_brand': brand,
                'detected_bank': bank,
                'period_from': period.get('from', ''),
                'period_to': period.get('to', ''),
                'period_label': period.get('label', ''),
                'debug_text_sample': extracted_text[:300],
            })

        summary = {
            'pdf_count': len(parsed_files),
            'bank_hint': self._normalize_bank_hint(bank_hint),
            'detected_brands': self._unique(detected_brands),
            'detected_banks': self._unique(detected_banks),
            'date_from': min(period_from_values) if period_from_values else '',
            'date_to': max(period_to_values) if period_to_values else '',
            'period_labels': self._unique([row['period_label'] for row in parsed_files if row.get('period_label')]),
        }

        result = {
            'files': parsed_files,
            'summary': summary,
        }

        return set_response(result, 200, '')

    @route('/prepare-draft', methods=['POST'])
    def prepare_draft(self):
        payload = request.get_json(silent=True) or {}

        account = str(payload.get('account') or '').strip()
        date_from = str(payload.get('date_from') or '').strip()
        date_to = str(payload.get('date_to') or '').strip()
        criterion = str(payload.get('criterion') or '').strip() or 'auto'
        bank = str(payload.get('bank') or '').strip()
        brand = str(payload.get('brand') or '').strip()
        pdf_count = int(payload.get('pdf_count') or 0)
        pdf_names = payload.get('pdf_names') or []

        if not account or not date_from or not date_to:
            return set_response([], 400, 'Debe indicar cuenta y rango de fechas para preparar la conciliacion.')

        parsed_from = self._parse_iso_date(date_from)
        parsed_to = self._parse_iso_date(date_to)
        if not parsed_from or not parsed_to:
            return set_response([], 400, 'Las fechas recibidas no son validas.')

        draft_id = self._build_conciliation_id()
        observation_parts = [
            'CONCILIACION TARJETAS',
            f'Banco: {bank or "No detectado"}',
            f'Tarjeta: {brand or "No detectada"}',
            f'Criterio: {criterion}',
            f'PDFs: {pdf_count}',
        ]
        if pdf_names:
            observation_parts.append('Archivos: ' + ', '.join([str(name).strip() for name in pdf_names[:3] if str(name).strip()]))
        observation_text = ' | '.join(observation_parts)[:255]

        sql = """
INSERT INTO dbo.MV_CONCILIACION_CAB
    (IdConciliacion, Fecha, Cuenta, Observaciones, Usuario, FechaDesde, FechaHasta, UNegocio, Finalizada, Tipo, FechaDesde2, FechaHasta2)
VALUES
    (?, GETDATE(), ?, ?, ?, ?, ?, NULL, 0, ?, NULL, NULL)
""".strip()

        connection = get_conn(self.token_global)
        if connection == '':
            return set_response([], 500, 'No se pudo obtener la conexion con la base seleccionada.')

        try:
            cursor = connection.cursor()
            cursor.execute(
                sql,
                draft_id,
                account,
                observation_text,
                self.code_account,
                parsed_from,
                parsed_to,
                'TJ',
            )
            connection.commit()
        except Exception as e:
            try:
                connection.rollback()
            except Exception:
                pass
            return set_response([], 500, f'No se pudo guardar el borrador de conciliacion. {e}')
        finally:
            try:
                connection.close()
            except Exception:
                pass

        return set_response({
            'id_conciliacion': draft_id,
            'account': account,
            'date_from': date_from,
            'date_to': date_to,
            'bank': bank or 'No detectado',
            'brand': brand or 'No detectada',
            'criterion': criterion,
            'pdf_count': pdf_count,
            'status': 'draft_created',
        }, 200, '')

    def _extract_pdf_text(self, file_item):
        try:
            raw_bytes = file_item.read() or b''
            file_item.stream.seek(0)

            if PdfReader is not None:
                reader = PdfReader(io.BytesIO(raw_bytes))
                text_parts = []
                for page in reader.pages[:8]:
                    text_parts.append(page.extract_text() or '')
                extracted = '\n'.join(text_parts).strip()
                if extracted:
                    return extracted

            return raw_bytes[:350000].decode('latin-1', errors='ignore')
        except Exception:
            try:
                file_item.stream.seek(0)
            except Exception:
                pass
            return ''

    def _normalize_bank_hint(self, bank_hint: str) -> str:
        mapping = {
            'auto': 'Detectar desde PDF',
            'banco-nacion': 'Banco Nacion',
            'banco-patagonia': 'Banco Patagonia',
            'prisma': 'Prisma',
            'fiserv': 'Fiserv / First Data',
            'mercado-pago': 'Mercado Pago',
            'otro': 'Otro / revisar manualmente',
        }
        return mapping.get(bank_hint, bank_hint or 'Detectar desde PDF')

    def _detect_brand(self, text: str) -> str:
        normalized = text.lower()
        patterns = [
            ('Mastercard', [r'mastercard', r'\bmaster\b']),
            ('Visa', [r'\bvisa\b']),
            ('Amex', [r'\bamex\b', r'american\s*express']),
            ('Cabal', [r'\bcabal\b']),
            ('Maestro', [r'\bmaestro\b']),
        ]

        for label, pattern_list in patterns:
            for pattern in pattern_list:
                if re.search(pattern, normalized, re.IGNORECASE):
                    return label

        return 'No detectada'

    def _detect_bank(self, text: str, bank_hint: str) -> str:
        normalized = text.lower()
        compact = self._compact_spaces(text)

        pagador_match = re.search(r'pagador\s*:?\s*(.+)', compact, re.IGNORECASE)
        if pagador_match:
            pagador_line = pagador_match.group(1)[:120]
            detected = self._match_known_bank(pagador_line)
            if detected:
                return detected

        detected = self._match_known_bank(normalized)
        if detected:
            return detected

        hardcoded_tokens = [
            ('Banco Patagonia', ['PATAGONIA', 'BANCO PATAGONIA']),
            ('Banco Nacion', ['BANCO NACION', 'NACION ARGENTINA']),
            ('Prisma', ['PAYWAY', 'PRISMA']),
            ('Fiserv / First Data', ['FISERV', 'FIRST DATA']),
        ]
        upper_text = text.upper()
        for label, tokens in hardcoded_tokens:
            if any(token in upper_text for token in tokens):
                return label

        normalized_hint = self._normalize_bank_hint(bank_hint)
        if normalized_hint != 'Detectar desde PDF':
            return normalized_hint

        return 'No detectado'

    def _match_known_bank(self, text: str):
        patterns = [
            ('Banco Patagonia', [r'banco\s+patagonia', r'patagonia\s+s\.a\.?', r'\bpatagonia\b']),
            ('Banco Nacion', [r'banco\s+nacion', r'banco\s+de\s+la\s+nacion', r'\bnacion\b']),
            ('Prisma', [r'\bprisma\b', r'payway']),
            ('Fiserv / First Data', [r'\bfiserv\b', r'first\s*data']),
            ('Mercado Pago', [r'mercado\s*pago']),
            ('Banco Santander', [r'\bsantander\b']),
            ('Banco Galicia', [r'\bgalicia\b']),
            ('BBVA', [r'\bbbva\b']),
        ]

        for label, pattern_list in patterns:
            for pattern in pattern_list:
                if re.search(pattern, text, re.IGNORECASE):
                    return label
        return None

    def _detect_period(self, text: str, filename: str):
        emission_date = self._extract_emission_date(text)
        if emission_date:
            return self._month_range(emission_date.year, emission_date.month)

        filename_date = self._extract_filename_date(filename)
        if filename_date:
            return self._month_range(filename_date.year, filename_date.month)

        return {}

    def _extract_emission_date(self, text: str):
        compact = self._compact_spaces(text)
        match = re.search(r'fecha\s+de\s+emision\s*:?\s*(\d{2})/(\d{2})/(20\d{2})', compact, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            return self._safe_date_parse(year, month, day)

        if self._is_monthly_summary(text):
            all_dates = self._extract_exact_dates(text)
            if all_dates:
                return max(all_dates)

        return None

    def _is_monthly_summary(self, text: str) -> bool:
        return bool(re.search(r'resumen\s+mensual\s+de\s+liquidaciones', text, re.IGNORECASE))

    def _extract_filename_date(self, filename: str):
        exact_date_match = re.search(r'(20\d{2})-(\d{2})-(\d{2})', filename)
        if exact_date_match:
            year, month, day = exact_date_match.groups()
            return self._safe_date_parse(year, month, day)

        compact_match = re.search(r'(20\d{2})(\d{1,2})(?!\d)', filename)
        if compact_match:
            year = compact_match.group(1)
            month = compact_match.group(2)
            return self._safe_date_parse(year, month, '01')

        return None

    def _extract_exact_dates(self, text: str):
        found = []

        for year, month, day in re.findall(r'(20\d{2})-(\d{2})-(\d{2})', text):
            parsed = self._safe_date_parse(year, month, day)
            if parsed:
                found.append(parsed)

        for day, month, year in re.findall(r'(\d{2})/(\d{2})/(20\d{2})', text):
            parsed = self._safe_date_parse(year, month, day)
            if parsed:
                found.append(parsed)

        return self._unique_dates(found)

    def _month_range(self, year: int, month: int):
        last_day = calendar.monthrange(year, month)[1]
        return {
            'from': f'{year}-{month:02d}-01',
            'to': f'{year}-{month:02d}-{last_day:02d}',
            'label': f'{year}-{month:02d}',
        }

    def _compact_spaces(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text or '').strip()

    def _safe_date_parse(self, year: str, month: str, day: str):
        try:
            return datetime(int(year), int(month), int(day))
        except Exception:
            return None

    def _parse_iso_date(self, value: str):
        try:
            return datetime.strptime(value, '%Y-%m-%d')
        except Exception:
            return None

    def _build_conciliation_id(self):
        return datetime.now().strftime('%y%m%d%H%M%S') + f'{random.randint(0, 99):02d}'

    def _unique_dates(self, values):
        unique = []
        keys = set()
        for value in values:
            if not value:
                continue
            key = value.strftime('%Y-%m-%d')
            if key not in keys:
                keys.add(key)
                unique.append(value)
        return unique

    def _unique(self, values):
        result = []
        seen = set()
        for value in values:
            current = (value or '').strip()
            if current and current not in seen:
                seen.add(current)
                result.append(current)
        return result