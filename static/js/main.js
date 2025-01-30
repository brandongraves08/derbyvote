// Check if user has already voted when page loads
document.addEventListener('DOMContentLoaded', function() {
    fetch('/check-vote')
        .then(response => response.json())
        .then(data => {
            if (data.has_voted) {
                // Disable all vote buttons if user has already voted
                document.querySelectorAll('.vote-btn').forEach(button => {
                    button.disabled = true;
                    button.textContent = 'Already Voted';
                    button.classList.remove('btn-primary');
                    button.classList.add('btn-secondary');
                });
            }
        });
});

let currentVoteCode = '';

function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('code-status');
    statusDiv.className = `alert alert-${type}`;
    statusDiv.textContent = message;
    statusDiv.classList.remove('d-none');
}

function validateCode() {
    const codeInput = document.getElementById('vote-code');
    const code = codeInput.value.trim();
    
    if (!/^\d{5}$/.test(code)) {
        showStatus('Please enter a valid 5-digit code', 'danger');
        return;
    }
    
    currentVoteCode = code;
    showStatus('Code validated! You can now vote for a car', 'success');
    
    // Enable all vote buttons
    document.querySelectorAll('.vote-btn').forEach(btn => {
        btn.disabled = false;
    });
}

function voteCar(carId) {
    if (!currentVoteCode) {
        showStatus('Please enter and validate your voting code first', 'danger');
        return;
    }

    const button = document.querySelector(`button[data-car-id="${carId}"]`);
    button.disabled = true;
    
    const formData = new FormData();
    formData.append('vote_code', currentVoteCode);
    
    fetch(`/vote/${carId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Vote failed');
        }
        return response.json();
    })
    .then(data => {
        // Show success message
        showStatus('Thank you for voting!', 'success');
        
        // Disable all vote buttons and clear the code
        document.querySelectorAll('.vote-btn').forEach(btn => {
            btn.disabled = true;
            btn.textContent = 'Vote Recorded';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
        });
        
        // Clear and disable the code input
        const codeInput = document.getElementById('vote-code');
        codeInput.value = '';
        codeInput.disabled = true;
        document.querySelector('button[onclick="validateCode()"]').disabled = true;
        
        currentVoteCode = '';
    })
    .catch(error => {
        console.error('Error:', error);
        button.disabled = false;
        showStatus('Invalid or already used voting code', 'danger');
        currentVoteCode = '';
        
        // Clear the code input
        document.getElementById('vote-code').value = '';
    });
}
