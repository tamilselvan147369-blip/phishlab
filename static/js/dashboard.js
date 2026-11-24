// dashboard.js
// Expects a global variable `statsData` injected by the template.
// Uses Chart.js to display a bar chart of campaign activity.

document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('activityChart').getContext('2d');
    if (!statsData || !Array.isArray(statsData)) {
        console.warn('No stats data available for Chart.js');
        return;
    }
    const labels = statsData.map(item => item.name);
    const emailsSent = statsData.map(item => item.emails_sent);
    const opens = statsData.map(item => item.opens);
    const clicks = statsData.map(item => item.clicks);
    const submissions = statsData.map(item => item.submits);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Emails Sent',
                    data: emailsSent,
                    backgroundColor: '#7DF9FF' // electric blue
                },
                {
                    label: 'Opens',
                    data: opens,
                    backgroundColor: '#FFCC00' // warning orange
                },
                {
                    label: 'Link Clicks',
                    data: clicks,
                    backgroundColor: '#AA00FF' // purple
                },
                {
                    label: 'Form Submissions',
                    data: submissions,
                    backgroundColor: '#FF4444' // danger red
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#E0E7FF'
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#E0E7FF' },
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: '#E0E7FF' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            }
        }
    });
});
