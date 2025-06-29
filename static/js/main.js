document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    const uploadArea = document.getElementById('upload-area');
    const previewContainer = document.getElementById('preview-container');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const loadingOverlay = document.getElementById('loading-overlay');
    const uploadModal = document.getElementById('upload-modal');
    const errorModal = document.getElementById('error-modal');
    const downloadModal = document.getElementById('download-modal');
    const themeToggle = document.getElementById('theme-toggle');

    let currentFileId = null;

    // Ensure all modals are hidden by default
    [uploadModal, errorModal, downloadModal].forEach(modal => {
        if (modal) {
            modal.classList.add('hidden');
        }
    });

    // Modal handling functions
    window.closeModal = (modalId) => {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
        }
    };

    function showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    // Close modal when clicking outside
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.add('hidden');
        }
    });

    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal').forEach(modal => {
                modal.classList.add('hidden');
            });
        }
    });

    // Theme Toggle
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const icon = themeToggle.querySelector('i');
        icon.classList.toggle('fa-moon');
        icon.classList.toggle('fa-sun');
    });

    // File Upload Handlers
    uploadBtn.addEventListener('click', () => {
        fileInput.click();
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length) {
            handleFileUpload(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileUpload(e.target.files[0]);
        }
    });

    async function handleFileUpload(file) {
        if (!file.name.endsWith('.docx')) {
            showError('Please upload a .docx file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        showModal('upload-modal');

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                currentFileId = data.file_id;
                closeModal('upload-modal');
                showPreview(currentFileId);
                addSystemMessage('Document uploaded successfully! How would you like me to format it?');
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            closeModal('upload-modal');
            showError(error.message);
        }
    }

    // Preview Handlers
    async function showPreview(fileId) {
        uploadArea.classList.add('hidden');
        previewContainer.classList.remove('hidden');
        
        try {
            const response = await fetch(`/api/preview/${fileId}`);
            const data = await response.json();
            
            if (response.ok) {
                const previewContent = document.getElementById('preview-content');
                previewContent.innerHTML = data.html;
            } else {
                throw new Error(data.error || 'Failed to load preview');
            }
        } catch (error) {
            showError(error.message);
        }
    }

    // Chat Handlers
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (!message || !currentFileId) return;

        addUserMessage(message);
        chatInput.value = '';
        showLoadingOverlay('Processing your request...');

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_id: currentFileId,
                    instructions: message
                })
            });

            const data = await response.json();

            if (response.ok) {
                addSystemMessage(data.message);
                showPreview(currentFileId); // Refresh preview
            } else {
                throw new Error(data.error || 'Processing failed');
            }
        } catch (error) {
            addSystemMessage('Error: ' + error.message, true);
        } finally {
            hideLoadingOverlay();
        }
    });

    // UI Helpers
    function addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        messageDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addSystemMessage(message, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message system${isError ? ' error' : ''}`;
        messageDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showError(message) {
        const errorMessage = document.getElementById('error-message');
        errorMessage.textContent = message;
        showModal('error-modal');
    }

    function showLoadingOverlay(message) {
        document.getElementById('loading-text').textContent = message;
        loadingOverlay.classList.remove('hidden');
    }

    function hideLoadingOverlay() {
        loadingOverlay.classList.add('hidden');
    }

    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initialize zoom controls
    const zoomIn = document.getElementById('zoom-in');
    const zoomOut = document.getElementById('zoom-out');
    const zoomLevel = document.getElementById('zoom-level');
    let currentZoom = 100;

    zoomIn.addEventListener('click', () => {
        if (currentZoom < 200) {
            currentZoom += 10;
            updateZoom();
        }
    });

    zoomOut.addEventListener('click', () => {
        if (currentZoom > 50) {
            currentZoom -= 10;
            updateZoom();
        }
    });

    function updateZoom() {
        zoomLevel.textContent = `${currentZoom}%`;
        const previewContent = document.getElementById('preview-content');
        previewContent.style.transform = `scale(${currentZoom / 100})`;
    }

    // Initialize download button
    const downloadBtn = document.getElementById('download-btn');
    const downloadDocBtn = document.getElementById('download-doc');

    downloadDocBtn.addEventListener('click', () => {
        if (currentFileId) {
            showModal('download-modal');
        }
    });

    downloadBtn.addEventListener('click', async () => {
        if (!currentFileId) return;
        
        try {
            const response = await fetch(`/api/download/${currentFileId}`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'formatted_document.docx';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                closeModal('download-modal');
            } else {
                const data = await response.json();
                throw new Error(data.error || 'Download failed');
            }
        } catch (error) {
            showError(error.message);
        }
    });

    // Initialize clear chat button
    const clearChatBtn = document.getElementById('clear-chat');
    clearChatBtn.addEventListener('click', () => {
        while (chatMessages.firstChild) {
            chatMessages.removeChild(chatMessages.firstChild);
        }
        addSystemMessage('Welcome to SmartDoc Formatter! Upload a document to get started.');
    });
}); 