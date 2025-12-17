const API_URL = "http://localhost:8000";

function log(data) {
    const output = document.getElementById('output');
    output.textContent = JSON.stringify(data, null, 2);
    const panel = document.getElementById('status-panel');
    panel.scrollTop = panel.scrollHeight;
}

async function apiCall(endpoint) {
    const output = document.getElementById('output');
    output.textContent = "Processing... (This might take a while)";
    
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST'
        });
        const data = await response.json();
        log(data);
    } catch (error) {
        log({ error: error.message });
    }
}

async function convertColor() {
    const r = document.getElementById('r').value;
    const g = document.getElementById('g').value;
    const b = document.getElementById('b').value;

    try {
        const response = await fetch(`${API_URL}/rgb-to-yuv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ r: parseFloat(r), g: parseFloat(g), b: parseFloat(b) })
        });
        log(await response.json());
    } catch (error) {
        log({ error: error.message });
    }
}

async function convertCodec() {
    const codec = document.getElementById('codec-select').value;
    const output = document.getElementById('output');
    output.textContent = `Converting to ${codec}... Please wait.`;

    try {
        const response = await fetch(`${API_URL}/p2/convert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codec: codec })
        });
        log(await response.json());
    } catch (error) {
        log({ error: error.message });
    }
}

async function uploadImage(endpoint) {
    const fileInput = document.getElementById('uploadFile');
    if (fileInput.files.length === 0) {
        alert("Please select a file first");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            body: formData
        });
        log(await response.json());
    } catch (error) {
        log({ error: error.message });
    }
}