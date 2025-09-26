document.addEventListener('DOMContentLoaded', function () {
    // Helper function to generate random colors for charts
    const getRandomColor = () => {
        const r = Math.floor(Math.random() * 255);
        const g = Math.floor(Math.random() * 255);
        const b = Math.floor(Math.random() * 255);
        return `rgba(${r}, ${g}, ${b}, 0.7)`;
    };

    // 1. Student Distribution by Course Chart (Dynamic Pie Chart)
    const studentDistCtx = document.getElementById('studentDistributionChart');
    let studentDistChart;

    const updateStudentDistributionChart = (academicYearId) => {
        fetch(`/reports/api/student-distribution/${academicYearId}`)
            .then(response => response.json())
            .then(data => {
                if (studentDistChart) {
                    studentDistChart.data.labels = data.labels;
                    studentDistChart.data.datasets[0].data = data.data;
                    studentDistChart.data.datasets[0].backgroundColor = data.labels.map(() => getRandomColor());
                    studentDistChart.update();
                } else {
                    studentDistChart = new Chart(studentDistCtx, {
                        type: 'pie',
                        data: {
                            labels: data.labels,
                            datasets: [{
                                label: 'Number of Students',
                                data: data.data,
                                backgroundColor: data.labels.map(() => getRandomColor()),
                                borderColor: '#fff',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'top',
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            let label = context.label || '';
                                            if (label) {
                                                label += ': ';
                                            }
                                            if (context.parsed !== null) {
                                                label += context.parsed;
                                            }
                                            return label + ' students';
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error fetching student distribution data:', error));
    };

    const academicYearFilter = document.getElementById('academicYearFilter');
    if (academicYearFilter) {
        // Initial chart load
        updateStudentDistributionChart(academicYearFilter.value);

        // Update chart on filter change
        academicYearFilter.addEventListener('change', (event) => {
            updateStudentDistributionChart(event.target.value);
        });
    }

    // 2. Admissions by Academic Year Chart (Bar Chart)
    const admissionsCtx = document.getElementById('admissionsByYearChart');
    if (admissionsCtx && typeof admissionsByYearData !== 'undefined') {
        new Chart(admissionsCtx, {
            type: 'bar',
            data: {
                labels: admissionsByYearData.labels,
                datasets: [{
                    label: 'New Admissions',
                    data: admissionsByYearData.data,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
});