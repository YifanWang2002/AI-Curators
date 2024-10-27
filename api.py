from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from prompt_based_exhibition.ArtSearch import ArtSearch
from prompt_based_exhibition.prompt_parser_beta import EntityParser
from prompt_based_exhibition.exhibition_curator import ExhibitionCurator
import pandas as pd
from run import generate_exhibitions

app = Flask(__name__)
CORS(app)

@app.route('/api/generate_exhibition', methods=['POST'])
def api_generate_exhibition():
    try:
        request_data = request.get_json()
        if not request_data or 'prompt' not in request_data:
            return jsonify({'error': 'No prompt provided'}), 400
        
        prompt = request_data['prompt']
        exhibitions = generate_exhibitions(prompt)
        
        # Format response to match the expected structure
        formatted_data = []
        for i, exhibition in enumerate(exhibitions[:3]):  # Limit to 3 exhibitions
            formatted_exhibition = {
                ",exhibition_id": exhibition["exhibition_id"],
                "title": exhibition["title"],
                "description": exhibition["description"],
                "art_pieces": exhibition.get("art_pieces", []),
                "curator_id": "",  # Placeholder
                "pieces_count": exhibition["pieces_count"]
            }
            formatted_data.append(formatted_exhibition)
            
        return jsonify(formatted_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001)) # 5001 for local testing
    app.run(host='0.0.0.0', port=port, debug=True)
