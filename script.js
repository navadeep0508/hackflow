function toggleForms() {
    const signInForm = document.getElementById('signin');
    const signUpForm = document.getElementById('signup');
    
    if (signInForm.style.display === 'none') {
        signInForm.style.display = 'block';
        signUpForm.style.display = 'none';
    } else {
        signInForm.style.display = 'none';
        signUpForm.style.display = 'block';
    }
}

document.querySelector('.sign-up-button').addEventListener('click', function() {
    // Add sign-up functionality here
    alert('Sign Up functionality to be implemented.');
});
