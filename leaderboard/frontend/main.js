// EPB Leaderboard Frontend JavaScript

const API_BASE = window.location.origin + '/api';

// Load leaderboard on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadLeaderboard();

    // Set up event listeners
    document.getElementById('provider-filter').addEventListener('change', loadLeaderboard);
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadStats();
        loadLeaderboard();
    });
});

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        document.getElementById('total-submissions').textContent = data.total_submissions || 0;
        document.getElementById('top-score').textContent = data.top_score ? data.top_score.toFixed(2) : '-';
        document.getElementById('top-model').textContent = data.top_model || '-';
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadLeaderboard() {
    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error');
    const tableEl = document.getElementById('leaderboard-table');
    const bodyEl = document.getElementById('leaderboard-body');

    // Show loading
    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';
    tableEl.style.display = 'none';

    try {
        // Get filter
        const provider = document.getElementById('provider-filter').value;

        // Fetch leaderboard
        const url = new URL(`${API_BASE}/leaderboard`);
        if (provider) {
            url.searchParams.append('provider', provider);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        const leaderboard = data.leaderboard || [];

        // Clear table
        bodyEl.innerHTML = '';

        if (leaderboard.length === 0) {
            errorEl.textContent = 'No submissions found. Be the first to submit!';
            errorEl.style.display = 'block';
            loadingEl.style.display = 'none';
            return;
        }

        // Populate table
        leaderboard.forEach((entry) => {
            const row = document.createElement('tr');

            // Rank
            const rankClass = entry.rank <= 3 ? `rank-${entry.rank}` : 'rank';
            row.innerHTML = `
                <td class="${rankClass}">#${entry.rank}</td>
                <td><strong>${escapeHtml(entry.model_name)}</strong></td>
                <td>${escapeHtml(entry.provider)}</td>
                <td class="score">${entry.scores.epb_truth.toFixed(2)}</td>
                <td>${entry.scores.mirror_loop_phi.toFixed(1)}</td>
                <td>${entry.scores.confab_persistence.toFixed(1)}</td>
                <td>${entry.scores.violation_contamination.toFixed(1)}</td>
                <td>${entry.scores.echo_drift.toFixed(1)}</td>
                <td><span class="certification cert-${entry.certification}">${entry.certification}</span></td>
                <td>${formatDate(entry.submitted_at)}</td>
            `;

            bodyEl.appendChild(row);
        });

        // Show table
        tableEl.style.display = 'table';
        loadingEl.style.display = 'none';

    } catch (error) {
        console.error('Error loading leaderboard:', error);
        errorEl.textContent = `Error loading leaderboard: ${error.message}`;
        errorEl.style.display = 'block';
        loadingEl.style.display = 'none';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '-';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString();
    }
}
