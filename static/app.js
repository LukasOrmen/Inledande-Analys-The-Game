if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark-mode');
    document.addEventListener('DOMContentLoaded', () => {
        document.body.classList.add('dark-mode');
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) toggleBtn.innerText = '☀️';
    });
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDark);
    document.getElementById('theme-toggle').innerText = isDark ? '☀️' : '🌙';
}

function copyRawProblemText(rawText, title, answerText) {
    let fullContent = "PROBLEM: " + title + "\n" + rawText;
    if (answerText && answerText.trim() !== "") {
        fullContent += "\n\nFACIT:\n" + answerText;
    }
    navigator.clipboard.writeText(fullContent).then(() => {
        const copyBtn = document.getElementById('copy-btn');
        if (copyBtn) {
            copyBtn.innerText = '✓';
            setTimeout(() => { copyBtn.innerText = '📋'; }, 2000);
        }
    });
}

document.addEventListener('keydown', function(event) {
    const activeTag = document.activeElement.tagName.toLowerCase();
    if (activeTag === 'input' || activeTag === 'textarea') return;

    const navPrev = document.getElementById('nav-prev');
    const navNext = document.getElementById('nav-next');
    const toggleForm = document.getElementById('toggle-form');
    const bookmarkForm = document.getElementById('bookmark-form');
    const backLink = document.getElementById('back-link');
    const copyBtn = document.getElementById('copy-btn');

    if (event.key === 'ArrowLeft' && navPrev && !navPrev.classList.contains('disabled')) navPrev.click();
    else if (event.key === 'ArrowRight' && navNext && !navNext.classList.contains('disabled')) navNext.click();
    else if ((event.key === ' ' || event.code === 'Space') && toggleForm) { event.preventDefault(); toggleForm.submit(); }
    else if ((event.key === 'b' || event.key === 'B') && bookmarkForm) bookmarkForm.submit();
    else if (event.key === 'Escape' && backLink) backLink.click();
    else if ((event.key === 'c' || event.key === 'C') && copyBtn) copyBtn.click();
});

function checkMcqAnswer(btn, selectedLetter) {
    const container = document.getElementById('mcq-container');
    if (!container) return;

    const correctLetter = container.dataset.correct;
    const allButtons = container.querySelectorAll('.mcq-btn');

    allButtons.forEach(b => {
        if (b.dataset.option === correctLetter) {
            b.classList.add('correct');
        }
    });

    if (selectedLetter !== correctLetter) {
        btn.classList.add('wrong');
    }

    const explanationBox = document.getElementById('mcq-explanation');
    if (explanationBox) {
        explanationBox.style.display = 'block';
    }
}

document.addEventListener('keydown', function(event) {
    const activeTag = document.activeElement.tagName.toLowerCase();
    if (activeTag === 'input' || activeTag === 'textarea') return;

    const key = event.key.toUpperCase();
    if (['A', 'B', 'C', 'D', 'E'].includes(key) && !event.metaKey && !event.ctrlKey) {
        const optionBtn = document.querySelector(`.mcq-btn[data-option="${key}"]`);
        if (optionBtn) optionBtn.click();
    }
});
