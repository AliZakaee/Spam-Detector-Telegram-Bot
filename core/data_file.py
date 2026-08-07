import csv


def count_labeled_messages(path):
    """Count data records in current and legacy labeled-message CSV files."""
    with open(path, "r", encoding="utf-8", newline="") as file:
        rows = csv.reader(file)
        first_row = next((row for row in rows if row), None)
        if first_row is None:
            return 0
        normalized_first_row = [cell.strip().lower() for cell in first_row]
        first_row_count = 0 if normalized_first_row == ["message", "label"] else 1
        return first_row_count + sum(1 for row in rows if row)
