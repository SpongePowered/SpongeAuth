/**
 * @param {!gapi.auth2.GoogleUser} googleUser
 */
const onGoogleSignIn = (googleUser) => {
  console.log("Google sign in has been finished successfully!")
  const form = document.querySelector('#form-glogin');
  form.querySelector('input[name="google_id_token"]').value =
      googleUser.getAuthResponse().id_token;
  window.gapi.auth2.getAuthInstance().signOut();
  form.submit();
};

const onGoogleSignInFailure = (err) => {
    console.error('Google sign in has failed:' + err.error + '!');
}

window['onGoogleSignIn'] = onGoogleSignIn;
window['onGoogleSignInFailure'] = onGoogleSignInFailure;

(function() {
// Automatically check "Uploaded avatar" radio button if user selects an avatar.
Array.prototype.forEach.call(
    document.querySelectorAll('.avatar-image-upload'), (el) => {
      const form = el.closest('form');
      const radioButton = form.querySelector(
          'input[type=radio][name=avatar_from][value=upload]');
      el.addEventListener('change', () => {
        if (el.value === '')
          return;
        radioButton.checked = true;
      });
    });
})();
