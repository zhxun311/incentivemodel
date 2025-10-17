// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const batchFileInput = document.getElementById('batchFileInput');
const singleModeBtn = document.getElementById('singleMode');
const batchModeBtn = document.getElementById('batchMode');
const uploadHint = document.getElementById('uploadHint');

const preview = document.getElementById('preview');
const previewImage = document.getElementById('previewImage');
const fileName = document.getElementById('fileName');

const batchPreview = document.getElementById('batchPreview');
const batchFileCount = document.getElementById('batchFileCount');
const batchFileList = document.getElementById('batchFileList');

const scoreButton = document.getElementById('scoreButton');
const loading = document.getElementById('loading');
const result = document.getElementById('result');
const batchResult = document.getElementById('batchResult');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');

const newUploadButton = document.getElementById('newUploadButton');
const newBatchButton = document.getElementById('newBatchButton');
const retryButton = document.getElementById('retryButton');

let currentMode = 'single';
let selectedFile = null;
let selectedFiles = [];

// Mode switching
singleModeBtn.addEventListener('click', () => {
    currentMode = 'single';
    singleModeBtn.classList.add('active');
    batchModeBtn.classList.remove('active');
    uploadHint.textContent = 'Supports: JPG, PNG, WEBP, GIF, BMP, TIFF';
    resetUpload();
});

batchModeBtn.addEventListener('click', () => {
    currentMode = 'batch';
    batchModeBtn.classList.add('active');
    singleModeBtn.classList.remove('active');
    uploadHint.textContent = 'Select multiple images (Ctrl/Cmd + Click)';
    resetUpload();
});

// Click to upload
uploadBox.addEventListener('click', () => {
    if (currentMode === 'single') {
        fileInput.click();
    } else {
        batchFileInput.click();
    }
});

// File selection - Single
fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});

// File selection - Batch
batchFileInput.addEventListener('change', (e) => {
    handleBatchSelect(e.target.files);
});

// Drag and drop
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');

    if (currentMode === 'single') {
        handleFileSelect(e.dataTransfer.files[0]);
    } else {
        handleBatchSelect(e.dataTransfer.files);
    }
});

// Handle single file selection
function handleFileSelect(file) {
    if (!file) return;

    if (!validateFile(file)) return;

    selectedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        fileName.textContent = file.name;
        uploadBox.style.display = 'none';
        preview.style.display = 'block';
        scoreButton.style.display = 'block';
        scoreButton.textContent = 'Score Receipt';
    };
    reader.readAsDataURL(file);
}

// Handle batch file selection
function handleBatchSelect(files) {
    if (!files || files.length === 0) return;

    selectedFiles = [];
    const validFiles = [];

    for (let file of files) {
        if (validateFile(file, false)) {
            selectedFiles.push(file);
            validFiles.push(file);
        }
    }

    if (validFiles.length === 0) {
        showError('No valid image files selected');
        return;
    }

    // Show batch preview
    batchFileCount.textContent = `${validFiles.length} image(s) selected`;
    batchFileList.innerHTML = '';

    validFiles.forEach((file, idx) => {
        const item = document.createElement('div');
        item.className = 'batch-file-item';
        item.textContent = `${idx + 1}. ${file.name}`;
        batchFileList.appendChild(item);
    });

    uploadBox.style.display = 'none';
    batchPreview.style.display = 'block';
    scoreButton.style.display = 'block';
    scoreButton.textContent = `Score ${validFiles.length} Receipt(s)`;
}

// Validate file
function validateFile(file, showErrorMsg = true) {
    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/bmp', 'image/tiff'];

    if (!validTypes.includes(file.type)) {
        if (showErrorMsg) {
            showError('Please upload a valid image file (JPG, PNG, WEBP, GIF, BMP, TIFF)');
        }
        return false;
    }

    if (file.size > 16 * 1024 * 1024) {
        if (showErrorMsg) {
            showError('File size must be less than 16MB');
        }
        return false;
    }

    return true;
}

// Score button click
scoreButton.addEventListener('click', async () => {
    if (currentMode === 'single') {
        await scoreSingle();
    } else {
        await scoreBatch();
    }
});

// Score single file
async function scoreSingle() {
    if (!selectedFile) return;

    scoreButton.style.display = 'none';
    result.style.display = 'none';
    error.style.display = 'none';
    loading.style.display = 'block';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to score receipt');
        }

        showResult(data);
    } catch (err) {
        showError(err.message);
    } finally {
        loading.style.display = 'none';
    }
}

// Score batch files
async function scoreBatch() {
    if (selectedFiles.length === 0) return;

    scoreButton.style.display = 'none';
    batchResult.style.display = 'none';
    error.style.display = 'none';
    loading.style.display = 'block';
    loading.querySelector('p').textContent = `Analyzing ${selectedFiles.length} receipts...`;

    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files[]', file);
    });

    try {
        const response = await fetch('/batch-upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to score receipts');
        }

        showBatchResult(data);
    } catch (err) {
        showError(err.message);
    } finally {
        loading.style.display = 'none';
        loading.querySelector('p').textContent = 'Analyzing receipt...';
    }
}

// Show single result
function showResult(data) {
    document.getElementById('points').textContent = data.points;
    document.getElementById('band').textContent = data.band;
    document.getElementById('band').className = `score-band ${data.band}`;
    document.getElementById('reason').textContent = data.reason;
    document.getElementById('encouragement').textContent = data.encouragement;

    if (data.tip) {
        document.getElementById('tip').textContent = data.tip;
        document.getElementById('tipItem').style.display = 'flex';
    } else {
        document.getElementById('tipItem').style.display = 'none';
    }

    result.style.display = 'block';
}

// Show batch result
function showBatchResult(data) {
    document.getElementById('batchSuccess').textContent = data.success;
    document.getElementById('batchFailed').textContent = data.failed;

    const resultsList = document.getElementById('batchResultsList');
    resultsList.innerHTML = '';

    data.results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'batch-result-item';
        div.innerHTML = `
            <div class="filename">${item.filename}</div>
            <div class="score-summary">
                <span class="mini-points">${item.points}</span>
                <span class="mini-band ${item.band}">${item.band}</span>
                <span style="flex:1; color: #666; font-size: 0.9em;">${item.reason}</span>
            </div>
        `;
        resultsList.appendChild(div);
    });

    if (data.errors.length > 0) {
        data.errors.forEach(errMsg => {
            const div = document.createElement('div');
            div.className = 'batch-result-item';
            div.innerHTML = `<div style="color: #c62828;">❌ ${errMsg}</div>`;
            resultsList.appendChild(div);
        });
    }

    batchResult.style.display = 'block';
}

// Show error
function showError(message) {
    errorMessage.textContent = message;
    error.style.display = 'block';
    scoreButton.style.display = 'none';
}

// Reset upload
function resetUpload() {
    selectedFile = null;
    selectedFiles = [];
    fileInput.value = '';
    batchFileInput.value = '';
    uploadBox.style.display = 'block';
    preview.style.display = 'none';
    batchPreview.style.display = 'none';
    scoreButton.style.display = 'none';
    result.style.display = 'none';
    batchResult.style.display = 'none';
    error.style.display = 'none';
    loading.style.display = 'none';
}

// Event listeners for reset buttons
newUploadButton.addEventListener('click', resetUpload);
newBatchButton.addEventListener('click', resetUpload);
retryButton.addEventListener('click', resetUpload);
