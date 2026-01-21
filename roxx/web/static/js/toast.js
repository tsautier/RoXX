/**
 * Toast Notification System
 * Usage:
 *   showToast('success', 'Success!', 'Operation completed successfully');
 *   showToast('error', 'Error!', 'Something went wrong');
 *   showToast('warning', 'Warning!', 'Please review this');
 *   showToast('info', 'Info', 'Here is some information');
 */

// Create toast container once
if (!document.getElementById('toast-container')) {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
}

const TOAST_ICONS = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
};

function showToast(type = 'info', title, message, duration = 5000) {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = TOAST_ICONS[type] || TOAST_ICONS.info;
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            ${message ? `<div class="toast-message">${message}</div>` : ''}
        </div>
        <button class="toast-close" onclick="removeToast(this.parentElement)">×</button>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => removeToast(toast), duration);
    }
    
    return toast;
}

function removeToast(toast) {
    if (!toast) return;
    
    toast.classList.add('removing');
    setTimeout(() => {
        if (toast.parentElement) {
            toast.parentElement.removeChild(toast);
        }
    }, 300);
}

// Convenience functions
function showSuccess(title, message, duration) {
    return showToast('success', title, message, duration);
}

function showError(title, message, duration) {
    return showToast('error', title, message, duration);
}

function showWarning(title, message, duration) {
    return showToast('warning', title, message, duration);
}

function showInfo(title, message, duration) {
    return showToast('info', title, message, duration);
}
