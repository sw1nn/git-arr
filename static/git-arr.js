/* Miscellaneous javascript functions for git-arr. */

/* Return the current timestamp. */
function now() {
    return (new Date().getTime() / 1000);
}

/* Return a human readable string telling "how long ago" for a timestamp. */
function how_long_ago(timestamp) {
    if (timestamp < 0)
        return "never";

	var seconds = Math.floor(now() - timestamp);

	var interval = Math.floor(seconds / (365 * 24 * 60 * 60));
	if (interval > 1)
		return interval + " years ago";

	interval = Math.floor(seconds / (30 * 24 * 60 * 60));
	if (interval > 1)
		return interval + " months ago";

	interval = Math.floor(seconds / (24 * 60 * 60));

	if (interval > 1)
		return interval + " days ago";
	interval = Math.floor(seconds / (60 * 60));

	if (interval > 1)
		return interval + " hours ago";

	interval = Math.floor(seconds / 60);
	if (interval > 1)
		return interval + " minutes ago";

    if (seconds > 1)
        return Math.floor(seconds) + " seconds ago";

    return "about now";
}

/* Go through the document and replace the contents of the span.age elements
 * with a human-friendly variant, and then show them. */
function replace_timestamps() {
    var elements = document.getElementsByClassName("age");
    for (var i = 0; i < elements.length; i++) {
        var e = elements[i];

        var timestamp = e.innerHTML;
        e.innerHTML = how_long_ago(timestamp);
        e.style.display = "inline";

        if (timestamp > 0) {
            var age = now() - timestamp;
            if (age < (2 * 60 * 60))
                e.className = e.className + " age-band0";
            else if (age < (3 * 24 * 60 * 60))
                e.className = e.className + " age-band1";
            else if (age < (30 * 24 * 60 * 60))
                e.className = e.className + " age-band2";
        }
    }
}

function toggle(id) {
    var e = document.getElementById(id);

    if (e.style.display == "") {
        e.style.display = "none"
    } else if (e.style.display == "none") {
        e.style.display = ""
    }
}

/* Table sorting functionality */
var currentSortColumn = -1;
var currentSortDirection = 'asc';

function sortTable(columnIndex, dataType) {
    var table = document.getElementById('repos-table');
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));

    // Determine sort direction
    if (currentSortColumn === columnIndex) {
        // Toggle direction if clicking the same column
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        // New column, default to ascending
        currentSortDirection = 'asc';
        currentSortColumn = columnIndex;
    }

    // Sort the rows
    rows.sort(function(a, b) {
        var cellA = a.cells[columnIndex];
        var cellB = b.cells[columnIndex];
        var valueA, valueB;

        if (dataType === 'number') {
            // For timestamp columns, use the data-timestamp attribute
            var spanA = cellA.querySelector('.age');
            var spanB = cellB.querySelector('.age');
            valueA = parseFloat(spanA.getAttribute('data-timestamp'));
            valueB = parseFloat(spanB.getAttribute('data-timestamp'));
        } else {
            // For string columns, use text content
            valueA = cellA.textContent.trim().toLowerCase();
            valueB = cellB.textContent.trim().toLowerCase();
        }

        var comparison = 0;
        if (valueA > valueB) {
            comparison = 1;
        } else if (valueA < valueB) {
            comparison = -1;
        }

        return currentSortDirection === 'asc' ? comparison : -comparison;
    });

    // Reorder the rows in the table
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });

    // Update sort indicators
    updateSortIndicators(columnIndex);
}

function updateSortIndicators(activeColumn) {
    var indicators = document.querySelectorAll('.sort-indicator');
    indicators.forEach(function(indicator, index) {
        if (index === activeColumn) {
            indicator.textContent = currentSortDirection === 'asc' ? ' ▲' : ' ▼';
        } else {
            indicator.textContent = '';
        }
    });
}
