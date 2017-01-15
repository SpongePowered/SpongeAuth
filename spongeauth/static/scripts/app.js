/**
 * @param {!gapi.auth2.GoogleUser} googleUser
 */
const onGoogleSignIn = (googleUser) => {
	const form = document.querySelector('#form-glogin');
	form.querySelector('input[name="google_id_token"]').value = googleUser.getAuthResponse().id_token;
	window.gapi.auth2.getAuthInstance().signOut();
	form.submit();
};

window['onGoogleSignIn'] = onGoogleSignIn;
