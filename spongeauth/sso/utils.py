def make_payload(user, nonce, request=None):
    avatar_url = user.avatar.get_absolute_url()
    if request is not None:
        avatar_url = request.build_absolute_uri(avatar_url)
    payload = {
        'nonce': nonce,
        'email': user.email,
        'external_id': user.pk,
        'username': user.username,
        'name': user.username,
        'avatar_url': avatar_url,
        'avatar_force_update': 'true',
        'custom.user_field_1': user.mc_username,
        'custom.user_field_2': user.gh_username,
        'custom.user_field_3': user.irc_nick,
    }
    return payload
