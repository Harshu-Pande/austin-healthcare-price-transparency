import os

def print_directory_structure(start_path, indent=''):
    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            print(f"{sub_indent}{file}")

# Use a raw string to avoid unicode escape errors
print_directory_structure(r"C:\Users\HPANDE\Desktop\Austin_Replit_app")


Austin_Replit_app/
    app.py
    data_processor.py
    static/
        css/
            style.css
        data/
            Austin_Aetna_PPO_data.csv
            Austin_BCBS_Essentials_data.csv
            Austin_Cigna_OAP_data.csv
            Austin_UHC_Options_PPO_data.csv
            summary_Austin_Aetna_PPO.csv
            summary_Austin_BCBS_Essentials.csv
            summary_Austin_Cigna_OAP.csv
            summary_Austin_UHC_Options_PPO.csv
        js/
            search.js
            stats.js
    templates/
        base.html
        index.html
        search.html
        search_results.html
        stats.html
        stats_results.html