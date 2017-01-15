/**
 * Externs for Google Platform APIs.
 */

/** @const */
var gapi = {};
window.gapi = gapi;

/** @const */
gapi.auth2 = {};

gapi.auth2.init = function() {};

/** @typedef {{access_token: string, id_token: string, login_hint: string, scope: string, expires_in: string, first_issued_at: string, expires_at: string}} */
gapi.auth2.AuthResponse;

/** @constructor */
gapi.auth2.BasicProfile = function() {};

/** @return {string} */
gapi.auth2.BasicProfile.prototype.getId = function() {};

/** @return {string} */
gapi.auth2.BasicProfile.prototype.getName = function() {};

/** @return {string} */
gapi.auth2.BasicProfile.prototype.getGivenName = function() {};

/** @return {string} */
gapi.auth2.BasicProfile.prototype.getFamilyName = function() {};

/** @return {string} */
gapi.auth2.BasicProfile.prototype.getImageUrl = function() {};

/** @return {string} */
gapi.auth2.BasicProfile.prototype.getEmail = function() {};

/** @constructor */
gapi.auth2.GoogleUser = function() {};

/** @return {?string} */
gapi.auth2.GoogleUser.prototype.getId = function() {};

/** @return {boolean} */
gapi.auth2.GoogleUser.prototype.isSignedIn = function() {};

/** @return {?string} */
gapi.auth2.GoogleUser.prototype.getHostedDomain = function() {};

/** @return {?string} */
gapi.auth2.GoogleUser.prototype.getGrantedScopes = function() {};

/** @return {!gapi.auth2.BasicProfile|undefined} */
gapi.auth2.GoogleUser.prototype.getBasicProfile = function() {};

/** @return {!gapi.auth2.AuthResponse} */
gapi.auth2.GoogleUser.prototype.getAuthResponse = function() {};

/** @return {!Promise} */
gapi.auth2.GoogleUser.prototype.reloadAuthResponse = function() {};

/**
 * @param {string} scopes
 * @return {boolean}
 */
gapi.auth2.GoogleUser.prototype.hasGrantedScopes = function(scopes) {};

gapi.auth2.GoogleUser.prototype.disconnect = function() {};

/** @constructor */
gapi.auth2.GoogleAuth = function() {};

gapi.auth2.GoogleAuth.prototype.isSignedIn = {
  /** @return {boolean} */
  get: function() {},

  /** @param {function(boolean)} listener */
  listen: function(listener) {},
};

/** @constructor */
gapi.auth2.SigninOptionsBuilder = function() {};

/**
 * @param {(!Object<string, string>|!gapi.auth2.SigninOptionsBuilder)=} options
 * @return {!Promise}
 */
gapi.auth2.GoogleAuth.prototype.signIn = function(options) {};

/**
 * @return {!Promise}
 */
gapi.auth2.GoogleAuth.prototype.signOut = function() {};

gapi.auth2.GoogleAuth.prototype.disconnect = function() {};

/**
 * @param {!Object<string, string>=} options
 */
gapi.auth2.GoogleAuth.prototype.grantOfflineAccess = function(options) {};

/**
 * @param {string} container
 * @param {!Object<string, string>=} options
 * @param {function()=} onsuccess
 * @param {function()=} onfailure
 */
gapi.auth2.GoogleAuth.prototype.attachClickHandler = function(container, options, onsuccess, onfailure) {};

gapi.auth2.GoogleAuth.prototype.currentUser = {
  /** @return {!gapi.auth2.GoogleUser} */
  get: function() {},

  /** @param {function(!gapi.auth2.GoogleUser)} listener */
  listen: function(listener) {},
};

/** @returns {!gapi.auth2.GoogleAuth} */
gapi.auth2.getAuthInstance = function() {};
