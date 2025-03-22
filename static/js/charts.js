/**
 * Charts for Attendance Management System
 * Using Chart.js
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize attendance overview chart on student dashboard
    initAttendanceOverviewChart();
    
    // Initialize attendance trend chart on student dashboard
    initAttendanceTrendChart();
    
    // Initialize course attendance chart on faculty dashboard
    initCourseAttendanceChart();
    
    // Initialize student performance chart on faculty dashboard
    initStudentPerformanceChart();
});

/**
 * Initialize attendance overview chart (pie chart)
 */
function initAttendanceOverviewChart() {
    const chartCanvas = document.getElementById('attendance-overview-chart');
    
    if(chartCanvas) {
        // Get data from data attributes
        const presentCount = parseInt(chartCanvas.getAttribute('data-present') || 0);
        const absentCount = parseInt(chartCanvas.getAttribute('data-absent') || 0);
        const lateCount = parseInt(chartCanvas.getAttribute('data-late') || 0);
        
        // Create chart
        const ctx = chartCanvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Present', 'Absent', 'Late'],
                datasets: [{
                    data: [presentCount, absentCount, lateCount],
                    backgroundColor: ['#38b000', '#d00000', '#ffb700'],
                    borderColor: ['#ffffff', '#ffffff', '#ffffff'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = presentCount + absentCount + lateCount;
                                const percentage = Math.round((context.raw / total) * 100);
                                return `${context.label}: ${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Initialize attendance trend chart (line chart)
 */
function initAttendanceTrendChart() {
    const chartCanvas = document.getElementById('attendance-trend-chart');
    
    if(chartCanvas) {
        // Get data from data attributes (JSON string)
        const trendDataStr = chartCanvas.getAttribute('data-trend');
        let trendData = [];
        
        try {
            if(trendDataStr) {
                trendData = JSON.parse(trendDataStr);
            }
        } catch(e) {
            console.error('Error parsing trend data:', e);
        }
        
        // Prepare data for chart
        const labels = trendData.map(item => item.month);
        const percentages = trendData.map(item => item.percentage);
        
        // Create chart
        const ctx = chartCanvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Attendance %',
                    data: percentages,
                    borderColor: '#4a6fa5',
                    backgroundColor: 'rgba(74, 111, 165, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Attendance Percentage'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Month'
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Attendance: ${context.raw}%`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Initialize course attendance chart (bar chart) for faculty dashboard
 */
function initCourseAttendanceChart() {
    const chartCanvas = document.getElementById('course-attendance-chart');
    
    if(chartCanvas) {
        // Get data from data attributes (JSON string)
        const courseDataStr = chartCanvas.getAttribute('data-courses');
        let courseData = [];
        
        try {
            if(courseDataStr) {
                courseData = JSON.parse(courseDataStr);
            }
        } catch(e) {
            console.error('Error parsing course data:', e);
        }
        
        // Prepare data for chart
        const labels = courseData.map(item => item.code);
        const percentages = courseData.map(item => item.attendance);
        
        // Create chart
        const ctx = chartCanvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Average Attendance %',
                    data: percentages,
                    backgroundColor: percentages.map(p => 
                        p >= 75 ? '#38b000' : (p >= 60 ? '#ffb700' : '#d00000')
                    ),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Average Attendance Percentage'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Course'
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Attendance: ${context.raw}%`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Initialize student performance chart (horizontal bar chart) for faculty dashboard
 */
function initStudentPerformanceChart() {
    const chartCanvas = document.getElementById('student-performance-chart');
    
    if(chartCanvas) {
        // Get data from data attributes (JSON string)
        const studentsDataStr = chartCanvas.getAttribute('data-students');
        let studentsData = [];
        
        try {
            if(studentsDataStr) {
                studentsData = JSON.parse(studentsDataStr);
            }
        } catch(e) {
            console.error('Error parsing students data:', e);
        }
        
        // Sort by attendance percentage
        studentsData.sort((a, b) => a.percentage - b.percentage);
        
        // Take only the top and bottom 5 students
        let displayData = [];
        if(studentsData.length > 10) {
            // Get bottom 5
            const bottom5 = studentsData.slice(0, 5);
            // Get top 5
            const top5 = studentsData.slice(-5);
            displayData = [...bottom5, ...top5];
        } else {
            displayData = studentsData;
        }
        
        // Prepare data for chart
        const labels = displayData.map(item => item.name);
        const percentages = displayData.map(item => item.percentage);
        
        // Create chart
        const ctx = chartCanvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Attendance %',
                    data: percentages,
                    backgroundColor: percentages.map(p => 
                        p >= 75 ? '#38b000' : (p >= 60 ? '#ffb700' : '#d00000')
                    ),
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Attendance Percentage'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Student'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Attendance: ${context.raw}%`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Update chart data
 */
function updateChartData(chartId, newData, newLabels) {
    const chart = Chart.getChart(chartId);
    
    if(chart) {
        chart.data.datasets[0].data = newData;
        
        if(newLabels) {
            chart.data.labels = newLabels;
        }
        
        chart.update();
    }
}
