import csv


def count_labeled_messages(path):
    """Count data records in a message,label CSV file, excluding its header."""
    with open(path, "r", encoding="utf-8", newline="") as file:
        rows = csv.reader(file)
        if next(rows, None) is None:
            return 0
        return sum(1 for row in rows if row)
