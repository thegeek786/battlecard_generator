document.addEventListener('DOMContentLoaded', function() {
    let competitorCount = 0;

    document.getElementById('add-competitor').addEventListener('click', function() {
        competitorCount++;
        const competitorsSection = document.getElementById('competitors-section');
        
        const competitorHTML = `
            <h3>Competitor ${competitorCount}</h3>
            <label for="competitor_name_${competitorCount}">Enter Competitor ${competitorCount} Name:</label>
            <input type="text" id="competitor_name_${competitorCount}" name="competitor_name_${competitorCount}" required>
            
            <label for="competitor_urls_${competitorCount}">Enter URLs for Competitor ${competitorCount} (comma-separated):</label>
            <textarea id="competitor_urls_${competitorCount}" name="competitor_urls_${competitorCount}" rows="4" required></textarea>
        `;
        
        competitorsSection.insertAdjacentHTML('beforeend', competitorHTML);
    });
});
