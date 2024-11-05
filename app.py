from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from data_processor import DataProcessor

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
    insurance_type = request.args.get('type', '')  # Make type optional with default empty string
    procedure = request.args.get('procedure')
    zipcode = request.args.get('zipcode')
    sort_by = request.args.get('sort', 'price')
    
    if not all([insurance_plan, procedure]):  # Updated validation check
        return render_template('search_results.html', 
                             results={"error": "Missing required parameters", "results": []})
    
    results = data_processor.get_search_results(insurance_plan, insurance_type, procedure, zipcode, sort_by)
    return render_template('search_results.html', results=results)

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