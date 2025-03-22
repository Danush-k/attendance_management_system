/**
 * Main JavaScript for Attendance Management System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and popovers
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Handle leave request approvals/rejections
    setupLeaveRequestButtons();
    
    // Handle class cancellation
    setupCancelClassButtons();
    
    // Router validation for marking attendance
    setupRouterValidation();
    
    // Initialize countdown timer for OTP
    setupOTPCountdown();
    
    // Initialize date pickers with validation
    setupDatePickers();
});

/**
 * Set up leave request approval/rejection buttons
 */
function setupLeaveRequestButtons() {
    const approveButtons = document.querySelectorAll('.approve-leave');
    const rejectButtons = document.querySelectorAll('.reject-leave');
    
    if(approveButtons.length > 0 || rejectButtons.length > 0) {
        // Handle approve buttons
        approveButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const requestId = this.getAttribute('data-request-id');
                processLeaveRequest(requestId, 'approve');
            });
        });
        
        // Handle reject buttons
        rejectButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const requestId = this.getAttribute('data-request-id');
                processLeaveRequest(requestId, 'reject');
            });
        });
    }
}

/**
 * Process a leave request (approve/reject)
 */
function processLeaveRequest(requestId, action) {
    // Confirm the action
    if(!confirm(`Are you sure you want to ${action} this leave request?`)) {
        return;
    }
    
    fetch(`/faculty/leave_request/${requestId}/${action}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ requestId })
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            // Show success message
            showAlert(data.message, 'success');
            
            // Update UI
            const requestRow = document.getElementById(`leave-request-${requestId}`);
            if(requestRow) {
                if(action === 'approve') {
                    requestRow.querySelector('.leave-status').innerHTML = '<span class="leave-approved">Approved</span>';
                } else {
                    requestRow.querySelector('.leave-status').innerHTML = '<span class="leave-rejected">Rejected</span>';
                }
                
                // Hide action buttons
                requestRow.querySelector('.leave-actions').innerHTML = 'Processed';
            }
        } else {
            showAlert(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while processing the request', 'error');
    });
}

/**
 * Set up cancel class buttons
 */
function setupCancelClassButtons() {
    const cancelButtons = document.querySelectorAll('.cancel-class');
    
    if(cancelButtons.length > 0) {
        cancelButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const sessionId = this.getAttribute('data-session-id');
                
                // Confirm cancellation
                if(!confirm('Are you sure you want to cancel this class? All students will be marked present automatically.')) {
                    return;
                }
                
                cancelClass(sessionId);
            });
        });
    }
}

/**
 * Cancel a class session
 */
function cancelClass(sessionId) {
    fetch(`/faculty/cancel_class/${sessionId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            showAlert(data.message, 'success');
            
            // Update UI
            const sessionRow = document.getElementById(`session-${sessionId}`);
            if(sessionRow) {
                sessionRow.querySelector('.session-status').innerHTML = '<span class="badge bg-secondary">Cancelled</span>';
                sessionRow.querySelector('.session-actions').innerHTML = 'Class cancelled';
            }
        } else {
            showAlert(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while cancelling the class', 'error');
    });
}

/**
 * Set up router validation for attendance marking
 */
function setupRouterValidation() {
    const markAttendanceForm = document.getElementById('mark-attendance-form');
    
    if(markAttendanceForm) {
        const courseSelect = document.getElementById('course-select');
        const routerIdField = document.getElementById('router_id');
        const submitButton = document.getElementById('submit-attendance');
        
        // When course changes, update router ID
        if(courseSelect) {
            courseSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const routerId = selectedOption.getAttribute('data-router-id');
                if(routerId) {
                    routerIdField.value = routerId;
                    
                    // Validate location
                    validateRouterLocation(routerId, selectedOption.value);
                }
            });
            
            // Trigger change event to set initial router ID
            if(courseSelect.options.length > 0) {
                courseSelect.dispatchEvent(new Event('change'));
            }
        }
    }
}

/**
 * Validate router location against course router
 */
function validateRouterLocation(routerId, courseId) {
    if(!routerId || !courseId) return;
    
    fetch('/api/validate_router', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            router_id: routerId,
            course_id: courseId
        })
    })
    .then(response => response.json())
    .then(data => {
        const locationStatus = document.getElementById('location-status');
        const submitButton = document.getElementById('submit-attendance');
        
        if(locationStatus && submitButton) {
            if(data.valid) {
                locationStatus.innerHTML = '<div class="alert alert-success">Location verified! You can mark attendance.</div>';
                submitButton.disabled = false;
            } else {
                locationStatus.innerHTML = '<div class="alert alert-danger">You are not in the correct location for this class.</div>';
                submitButton.disabled = true;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        
        const locationStatus = document.getElementById('location-status');
        if(locationStatus) {
            locationStatus.innerHTML = '<div class="alert alert-warning">Unable to verify location. Please try again.</div>';
        }
    });
}

/**
 * Set up OTP countdown timer
 */
function setupOTPCountdown() {
    const otpExpiryElement = document.getElementById('otp-expiry');
    
    if(otpExpiryElement) {
        const expiryTime = otpExpiryElement.getAttribute('data-expiry');
        
        if(expiryTime) {
            const expiryDate = new Date(expiryTime);
            
            // Update countdown every second
            const countdownInterval = setInterval(function() {
                const now = new Date();
                const distance = expiryDate - now;
                
                // Time calculations
                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);
                
                // Display countdown
                otpExpiryElement.textContent = `OTP expires in ${minutes}m ${seconds}s`;
                
                // If expired, show message
                if(distance < 0) {
                    clearInterval(countdownInterval);
                    otpExpiryElement.textContent = "OTP has expired";
                    otpExpiryElement.classList.add('text-danger');
                    
                    const otpDisplay = document.getElementById('otp-display');
                    if(otpDisplay) {
                        otpDisplay.textContent = "EXPIRED";
                        otpDisplay.classList.add('text-danger');
                    }
                }
            }, 1000);
        }
    }
}

/**
 * Set up date pickers with validation
 */
function setupDatePickers() {
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if(startDateInput && endDateInput) {
        // Set min date to today
        const today = new Date().toISOString().split('T')[0];
        startDateInput.setAttribute('min', today);
        endDateInput.setAttribute('min', today);
        
        // Validate end date is after start date
        startDateInput.addEventListener('change', function() {
            endDateInput.setAttribute('min', this.value);
            
            // If end date is now before start date, reset it
            if(endDateInput.value && endDateInput.value < this.value) {
                endDateInput.value = this.value;
            }
        });
    }
}

/**
 * Show an alert message
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    // Add message
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to page
    const container = document.querySelector('.container');
    if(container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Automatically remove after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
}
