// Main client-side scripts
document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // File input size validation hint (10MB)
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                const maxBytes = 10 * 1024 * 1024;
                if (this.files[0].size > maxBytes) {
                    alert('Selected file exceeds the maximum allowed size of 10 MB.');
                    this.value = '';
                }
            }
        });
    }
});
