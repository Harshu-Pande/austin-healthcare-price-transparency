from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
from data_processor import DataProcessor
import io

app = Flask(__name__)

# Initialize data processor
data_processor = DataProcessor('static/data')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    insurance_plans = data_processor.get_insurance_plans()
    return render_template('search.html', insurance_plans=insurance_plans)

@app.route('/api/procedures')
def get_procedures():
    insurance_plan = request.args.get('plan', '')
    insurance_type = request.args.get('type', '')
    search_term = request.args.get('term', '')
    procedures = data_processor.search_procedures(insurance_plan, insurance_type, search_term)
    return jsonify(procedures)

@app.route('/search_results')
def search_results():
    insurance_plan = request.args.get('plan')
    insurance_type = request.args.get('type', '')
    procedure = request.args.get('procedure')
    zipcode = request.args.get('zipcode')
    sort_by = request.args.get('sort', 'price')
    provider = request.args.get('provider')
    min_price = float(request.args.get('min_price')) if request.args.get('min_price') else None
    max_price = float(request.args.get('max_price')) if request.args.get('max_price') else None
    distance = int(request.args.get('distance')) if request.args.get('distance') else None
    
    if not all([insurance_plan, procedure]):
        return render_template('search_results.html', 
                             results={"error": "Missing required parameters", "results": []})
    
    results = data_processor.get_search_results(
        insurance_plan=insurance_plan,
        insurance_type=insurance_type,
        procedure=procedure,
        zipcode=zipcode,
        sort_by=sort_by,
        provider=provider,
        min_price=min_price,
        max_price=max_price,
        distance=distance
    )
    return render_template('search_results.html', results=results)

@app.route('/export_results')
def export_results():
    insurance_plan = request.args.get('plan')
    insurance_type = request.args.get('type', '')
    procedure = request.args.get('procedure')
    zipcode = request.args.get('zipcode')
    sort_by = request.args.get('sort', 'price')
    provider = request.args.get('provider')
    min_price = float(request.args.get('min_price')) if request.args.get('min_price') else None
    max_price = float(request.args.get('max_price')) if request.args.get('max_price') else None
    distance = int(request.args.get('distance')) if request.args.get('distance') else None

    if not all([insurance_plan, procedure]):
        return "Missing required parameters", 400

    results = data_processor.get_search_results(
        insurance_plan=insurance_plan,
        insurance_type=insurance_type,
        procedure=procedure,
        zipcode=zipcode,
        sort_by=sort_by,
        provider=provider,
        min_price=min_price,
        max_price=max_price,
        distance=distance
    )

    csv_data = data_processor.export_search_results(results)
    if not csv_data:
        return "No data to export", 404

    filename = f"healthcare_prices_{procedure.replace(' ', '_')}.csv"
    return send_file(
        io.StringIO(csv_data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/api/stats_data')
def get_stats_data():
    procedure = request.args.get('procedure')
    if not procedure:
        return jsonify({"error": "Procedure parameter is required"})
    stats_data = data_processor.get_stats_data(procedure)
    return jsonify(stats_data)

@app.route('/stats_results')
def stats_results():
    procedure = request.args.get('procedure')
    if not procedure:
        return render_template('stats_results.html', error="Procedure parameter is required")
    return render_template('stats_results.html', procedure=procedure)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
