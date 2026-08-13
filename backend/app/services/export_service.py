import csv
import io
import json

from app.domain.models import ParseResult


class ExportService:
    @staticmethod
    def as_json(result: ParseResult) -> str:
        return result.model_dump_json(indent=2)

    @staticmethod
    def as_csv(result: ParseResult) -> str:
        output = io.StringIO(newline="")
        fields = [
            "fund_name",
            "report_date",
            "security_name",
            "security_type",
            "country_iso3",
            "sector",
            "number_of_shares",
            "principal_amount",
            "market_value",
            "source_page",
            "parser_source",
            "validation_status",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for record in result.holdings:
            data = record.model_dump(mode="json")
            writer.writerow({field: data.get(field) for field in fields})
        return output.getvalue()

    @staticmethod
    def json_preview(result: ParseResult, limit: int = 20) -> str:
        payload = result.model_dump(mode="json")
        payload["holdings"] = payload["holdings"][:limit]
        return json.dumps(payload, indent=2)
