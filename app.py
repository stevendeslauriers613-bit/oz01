import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def format_inventory_report(input_csv_path, output_xlsx_path):
    # Standard Accountant Category Order (20 categories)
    accountant_order = [
        "Beverages",
        "Dried Flower",
        "Edibles",
        "Extracts Ingested",
        "Extracts Inhaled",
        "Infused Pre-Rolls",
        "Milled Flower",
        "Pre-Rolls",
        "Seeds",
        "Topicals",
        "Vapes - Disposables",
        "Vapes - 510 Threads",
        "Vapes - Pods",
        "__SPACER__",  # Will become the blank row after row 14
        "Accessories",
        "Apparel / Swag",
        "Gift Cards",
        "Other Income",
        "Raffles",
        "System Fees",
        "Uniforms"
    ]

    # Load CSV data
    df = pd.read_csv(input_csv_path)
    
    # Strip existing total/sum rows or child rows starting with '>'
    if 'Category' in df.columns:
        df = df[~df['Category'].astype(str).str.strip().str.startswith('>')]
        df = df[~df['Category'].astype(str).str.strip().str.lower().str.contains('total')]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventory Summary"

    # Get headers from CSV (excluding Category if handled separately, or keep all)
    headers = list(df.columns)
    ws.append(headers)

    # Style Header (Dark Green #065F46 with Bold White Text)
    header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='D4D4D8'),
        right=Side(style='thin', color='D4D4D8'),
        top=Side(style='thin', color='D4D4D8'),
        bottom=Side(style='thin', color='D4D4D8')
    )

    # Iterate through the accountant order and write rows cleanly
    for target_cat in accountant_order:
        if target_cat == "__SPACER__":
            # Insert a completely blank row (Row 15) after Vapes - Pods
            ws.append([None] * len(headers))
            continue

        # Find matching row in uploaded CSV
        matched = df[df['Category'].astype(str).str.strip().str.lower() == target_cat.strip().lower()]
        
        if not matched.empty:
            row_vals = [matched.iloc[0][h] for h in headers]
        else:
            # Default empty row for missing categories
            row_vals = [target_cat] + [0.00] * (len(headers) - 1)

        ws.append(row_vals)
        current_row = ws.max_row

        # Apply borders and number formatting
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=current_row, column=col_num)
            cell.border = thin_border
            if col_num == 1:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = Font(name="Calibri", size=11, color="18181B")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.font = Font(name="Calibri", size=11, color="18181B")
                try:
                    cell.value = float(str(cell.value).replace('$', '').replace(',', ''))
                    cell.number_format = '#,##0.00'
                except ValueError:
                    pass

    wb.save(output_xlsx_path)
    print(f"Successfully formatted and saved to {output_xlsx_path}")
