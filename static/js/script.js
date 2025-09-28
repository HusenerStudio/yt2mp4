class YouTubeDownloader {
    constructor() {
        this.form = document.getElementById('downloadForm');
        this.urlInput = document.getElementById('youtubeUrl');
        this.qualitySelect = document.getElementById('qualitySelect');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.progressContainer = document.getElementById('progressContainer');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.videoInfoContainer = document.getElementById('videoInfoContainer');
        this.videoThumbnail = document.getElementById('videoThumbnail');
        this.videoTitle = document.getElementById('videoTitle');
        this.videoUploader = document.getElementById('videoUploader');
        this.videoDuration = document.getElementById('videoDuration');
        this.videoViews = document.getElementById('videoViews');
        this.videoDescription = document.getElementById('videoDescription');
        this.confirmDownloadBtn = document.getElementById('confirmDownloadBtn');
        this.cancelBtn = document.getElementById('cancelBtn');
        this.resultContainer = document.getElementById('resultContainer');
        this.successMessage = document.getElementById('successMessage');
        this.downloadLink = document.getElementById('downloadLink');
        this.fileName = document.getElementById('fileName');
        this.errorContainer = document.getElementById('errorContainer');
        this.errorText = document.getElementById('errorText');
        
        this.currentVideoInfo = null;
        
        this.init();
    }

    init() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.confirmDownloadBtn.addEventListener('click', () => this.confirmDownload());
        this.cancelBtn.addEventListener('click', () => this.cancelVideoInfo());
        this.setupPasteDetection();
        this.setupInputValidation();
    }

    setupPasteDetection() {
        this.urlInput.addEventListener('paste', (e) => {
            setTimeout(() => {
                this.validateUrl();
            }, 100);
        });
    }

    setupInputValidation() {
        this.urlInput.addEventListener('input', () => {
            this.validateUrl();
        });

        this.urlInput.addEventListener('blur', () => {
            this.validateUrl();
        });
    }

    validateUrl() {
        const url = this.urlInput.value.trim();
        if (!url) {
            this.urlInput.setCustomValidity('');
            return;
        }

        // Basic YouTube URL validation
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
        if (!youtubeRegex.test(url)) {
            this.urlInput.setCustomValidity('Please enter a valid YouTube URL');
        } else {
            this.urlInput.setCustomValidity('');
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const url = this.urlInput.value.trim();
        
        if (!url) {
            this.showError('Please enter a YouTube URL');
            return;
        }

        // Validate YouTube URL format
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
        if (!youtubeRegex.test(url)) {
            this.showError('Please enter a valid YouTube URL');
            return;
        }

        this.setLoadingState(true);
        this.hideError();
        this.hideResult();
        this.hideVideoInfo();

        try {
            await this.getVideoInfo(url);
        } catch (error) {
            console.error('Video info error:', error);
            this.showError(error.message || 'Failed to get video information. Please try again.');
            this.setLoadingState(false);
        }
    }

    async getVideoInfo(url) {
        this.updateProgress(0, 'Getting video information...');
        this.showProgress();

        try {
            const response = await fetch('/video-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (data.success) {
                this.currentVideoInfo = { url, ...data };
                this.displayVideoInfo(data);
                this.hideProgress();
                this.setLoadingState(false);
            } else {
                throw new Error(data.error || 'Failed to get video information');
            }
        } catch (error) {
            this.hideProgress();
            throw error;
        }
    }

    displayVideoInfo(info) {
        // Set thumbnail
        if (info.thumbnail) {
            this.videoThumbnail.src = info.thumbnail;
            this.videoThumbnail.alt = info.title || 'Video thumbnail';
        }

        // Set video details
        this.videoTitle.textContent = info.title || 'Unknown Title';
        this.videoUploader.textContent = info.uploader || 'Unknown Uploader';
        this.videoDuration.textContent = info.duration || 'Unknown Duration';
        this.videoViews.textContent = info.view_count || 'Unknown Views';
        
        // Set description (truncate if too long)
        const description = info.description || 'No description available';
        this.videoDescription.textContent = description.length > 200 
            ? description.substring(0, 200) + '...' 
            : description;

        this.showVideoInfo();
    }

    confirmDownload() {
        if (!this.currentVideoInfo) return;

        const quality = this.qualitySelect.value;
        this.hideVideoInfo();
        this.downloadVideo(this.currentVideoInfo.url, quality);
    }

    cancelVideoInfo() {
        this.hideVideoInfo();
        this.currentVideoInfo = null;
        this.setLoadingState(false);
    }

    async downloadVideo(url, quality = 'hd') {
        this.showProgress();
        this.updateProgress(0, `Starting download in ${quality.toUpperCase()} quality...`);

        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    url: url,
                    quality: quality 
                })
            });

            const data = await response.json();

            if (data.success) {
                this.updateProgress(100, 'Download completed!');
                setTimeout(() => {
                    this.hideProgress();
                    this.showResult(data.filename, data.title);
                    this.setLoadingState(false);
                    this.currentVideoInfo = null;
                }, 1000);
            } else {
                throw new Error(data.error || 'Download failed');
            }
        } catch (error) {
            this.hideProgress();
            throw error;
        }
    }

    updateProgress(percentage, text) {
        this.progressFill.style.width = percentage + '%';
        this.progressText.textContent = text;
    }

    showProgress() {
        this.progressContainer.style.display = 'block';
        this.progressContainer.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }

    hideProgress() {
        this.progressContainer.style.display = 'none';
        this.updateProgress(0, 'Processing...');
    }

    showVideoInfo() {
        this.videoInfoContainer.style.display = 'block';
        this.videoInfoContainer.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }

    hideVideoInfo() {
        this.videoInfoContainer.style.display = 'none';
    }

    showResult(filename, title) {
        this.fileName.textContent = filename;
        this.downloadLink.href = `/download-file/${encodeURIComponent(filename)}`;
        this.resultContainer.style.display = 'block';
        
        // Add animation class
        this.resultContainer.classList.add('pulse');
        
        // Auto-scroll to result
        this.resultContainer.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }

    showError(message) {
        this.errorText.textContent = message;
        this.errorContainer.style.display = 'block';
        
        // Auto-scroll to error
        this.errorContainer.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
    }

    hideError() {
        this.errorContainer.style.display = 'none';
    }

    hideResult() {
        this.resultContainer.style.display = 'none';
        this.resultContainer.classList.remove('pulse');
    }

    setLoadingState(loading) {
        if (loading) {
            this.downloadBtn.disabled = true;
            this.downloadBtn.innerHTML = '<i class="fas fa-spinner loading"></i> Processing...';
        } else {
            this.downloadBtn.disabled = false;
            this.downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download MP4';
        }
    }

    // Utility method to format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize the downloader when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new YouTubeDownloader();
    
    // Add some interactive effects
    const inputs = document.querySelectorAll('input, button, a');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('focus');
        });
        
        input.addEventListener('blur', () => {
            input.parentElement.classList.remove('focus');
        });
    });

    // Add keyboard shortcut (Ctrl+Enter to submit)
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            const form = document.getElementById('downloadForm');
            if (form) {
                const event = new Event('submit', { cancelable: true });
                form.dispatchEvent(event);
            }
        }
    });

    // Show welcome message
    console.log('yt2mp4 - YouTube to MP4 Downloader initialized');
});

// Service Worker registration for offline functionality (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Error handling for uncaught errors
window.addEventListener('error', (e) => {
    console.error('Application error:', e.error);
});

// Handle offline/online status
window.addEventListener('online', () => {
    console.log('Application is online');
});

window.addEventListener('offline', () => {
    console.log('Application is offline');
});