const onGoogleSignIn = (googleUser) => {
	const profile = googleUser.getBasicProfile();
	const form = document.querySelector('#form-glogin');
	form.querySelector('input[name="google_id_token"]').value = googleUser.getAuthResponse().id_token;
	gapi.auth2.getAuthInstance().signOut();
	form.submit();
};
