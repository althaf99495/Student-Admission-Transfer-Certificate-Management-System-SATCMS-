import csv
import io

def generate_csv_from_data(data, headers):
    """
    Generates a CSV file in-memory from a list of dictionaries.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(data)
    
    # Ensure all data is written to the buffer
    output.seek(0)
    
    return output.getvalue()
