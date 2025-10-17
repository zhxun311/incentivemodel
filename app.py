"""Flask web application for receipt scoring with image upload."""
import os
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from incentive_scorer import IncentiveScorer
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['EXAMPLES_FOLDER'] = 'examples'

# Supported image extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'tif'}

# Create folders if they don't exist
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(exist_ok=True)
Path(app.config['EXAMPLES_FOLDER']).mkdir(exist_ok=True)

scorer = IncentiveScorer(model="gpt-5-nano")


def allowed_file(filename):
    """Check if file has an allowed image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and scoring."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only image files are supported (JPG, PNG, WEBP, GIF, BMP, TIFF)'}), 400

    try:
        # Save uploaded file to temp location
        filename = secure_filename(file.filename)
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_filepath)

        # Score the file
        result = scorer.score_file(temp_filepath)

        # Save image to examples folder
        import shutil
        import time
        timestamp = int(time.time())
        saved_filename = f"{Path(filename).stem}_{timestamp}{Path(filename).suffix}"
        examples_filepath = os.path.join(app.config['EXAMPLES_FOLDER'], saved_filename)
        shutil.copy2(temp_filepath, examples_filepath)

        # Save JSON output
        output_filename = f"{Path(saved_filename).stem}_scored.json"
        output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        import json
        output_data = {
            'schema_version': result.schema_version,
            'points': result.points,
            'band': result.band,
            'reason': result.reason,
            'encouragement': result.encouragement,
            'tip': result.tip,
            'extracted_text': result.extracted_text,
            'original_filename': filename,
            'saved_filename': saved_filename
        }

        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # Clean up temp file
        os.remove(temp_filepath)

        # Return only the score (without extracted_text)
        return jsonify({
            'schema_version': result.schema_version,
            'points': result.points,
            'band': result.band,
            'reason': result.reason,
            'encouragement': result.encouragement,
            'tip': result.tip,
            'saved_image': saved_filename,
            'saved_json': output_filename
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/batch-upload', methods=['POST'])
def batch_upload():
    """Handle multiple file uploads and scoring."""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files[]')

    if not files or len(files) == 0:
        return jsonify({'error': 'No files selected'}), 400

    results = []
    errors = []

    for idx, file in enumerate(files):
        if file.filename == '':
            continue

        if not allowed_file(file.filename):
            errors.append(f"{file.filename}: Only image files supported")
            continue

        try:
            # Save uploaded file to temp location
            filename = secure_filename(file.filename)
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(temp_filepath)

            # Score the file with batch context
            batch_context = {
                'total_files_in_batch': len(files),
                'file_position': idx + 1
            }
            result = scorer.score_file(temp_filepath, batch_context=batch_context)

            # Save image to examples folder
            import shutil
            import time
            timestamp = int(time.time())
            saved_filename = f"{Path(filename).stem}_{timestamp}{Path(filename).suffix}"
            examples_filepath = os.path.join(app.config['EXAMPLES_FOLDER'], saved_filename)
            shutil.copy2(temp_filepath, examples_filepath)

            # Save JSON output
            output_filename = f"{Path(saved_filename).stem}_scored.json"
            output_filepath = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

            import json
            output_data = {
                'schema_version': result.schema_version,
                'points': result.points,
                'band': result.band,
                'reason': result.reason,
                'encouragement': result.encouragement,
                'tip': result.tip,
                'extracted_text': result.extracted_text,
                'original_filename': filename,
                'saved_filename': saved_filename,
                'batch_context': batch_context
            }

            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            # Clean up temp file
            os.remove(temp_filepath)

            # Add to results
            results.append({
                'filename': filename,
                'schema_version': result.schema_version,
                'points': result.points,
                'band': result.band,
                'reason': result.reason,
                'encouragement': result.encouragement,
                'tip': result.tip,
                'saved_image': saved_filename,
                'saved_json': output_filename
            })

        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    return jsonify({
        'success': len(results),
        'failed': len(errors),
        'results': results,
        'errors': errors
    })


@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files."""
    return send_from_directory('static', path)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
