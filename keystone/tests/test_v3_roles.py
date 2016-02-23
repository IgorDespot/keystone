# Copyright (C) 2014 Universidad Politecnica de Madrid
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import uuid

from urllib import urlencode

from keystone import config
from keystone.common import dependency
from keystone.contrib.roles import core
from keystone.tests import test_v3
from keystone.tests import test_v3_oauth2

CONF = config.CONF

class RolesBaseTests(test_v3.RestfulTestCase):

    EXTENSION_NAME = 'roles'
    EXTENSION_TO_ADD = 'roles_extension'

    CONSUMER_URL = '/OS-OAUTH2/consumers'
    DEFAULT_REDIRECT_URIS = [
        'https://%s.com' %uuid.uuid4().hex,
        'https://%s.com' %uuid.uuid4().hex
    ]
    DEFAULT_SCOPES = [
        uuid.uuid4().hex,
        uuid.uuid4().hex,
        'all_info'
    ]

    ROLES_URL = '/OS-ROLES/roles'
    PERMISSIONS_URL = '/OS-ROLES/permissions'

    USER_ASSIGNMENTS_URL = '/OS-ROLES/users/role_assignments'
    USER_ROLES_URL = '/OS-ROLES/users/{user_id}/organizations/{organization_id}/applications/{application_id}/roles/{role_id}'
    USER_DEFAULT_ORG_ROLES_URL = '/OS-ROLES/users/{user_id}/applications/{application_id}/roles/{role_id}'
    
    ORGANIZATION_ASSIGNMENTS_URL = '/OS-ROLES/organizations/role_assignments'
    ORGANIZATION_ROLES_URL = '/OS-ROLES/organizations/{organization_id}/applications/{application_id}/roles/{role_id}'

    USER_ALLOWED_ROLES_URL = '/OS-ROLES/users/{user_id}/organizations/{organization_id}/roles/allowed'
    ORGANIZATION_ALLOWED_ROLES_URL = '/OS-ROLES/organizations/{organization_id}/roles/allowed'

    USER_ALLOWED_APPLICATIONS_URL = '/OS-ROLES/users/{user_id}/organizations/{organization_id}/applications/allowed'
    ORGANIZATION_ALLOWED_APPLICATIONS_URL = '/OS-ROLES/organizations/{organization_id}/applications/allowed'

    USER_ALLOWED_MANAGE_ROLES_URL = '/OS-ROLES/users/{user_id}/organizations/{organization_id}/applications/allowed_roles'
    ORGANIZATION_ALLOWED_MANAGE_ROLES_URL = '/OS-ROLES/organizations/{organization_id}/applications/allowed_roles'


    def setUp(self):
        super(RolesBaseTests, self).setUp()

        # Now that the app has been served, we can query CONF values
        self.base_url = 'http://localhost/v3'
        # NOTE(garcianavalon) I've put this line for dependency injection to work, 
        # but I don't know if its the right way to do it...
        self.manager = core.RolesManager()

    def new_fiware_role_ref(self, name, application=False, is_internal=False):
        role_ref = {
            'name': name,
            'application_id': application if application else uuid.uuid4().hex,
        }
        if is_internal:
            role_ref['is_internal'] = True
        return role_ref

    def _create_role(self, role_ref=None):
        if not role_ref:
            role_ref = self.new_fiware_role_ref(uuid.uuid4().hex)
        response = self.post(self.ROLES_URL, body={'role': role_ref})

        return response.result['role']

    def new_fiware_permission_ref(self, name, application=False, is_internal=False):
        permission_ref = {
            'name': name,
            'application_id': application if application else uuid.uuid4().hex,  
        }
        if is_internal:
            permission_ref['is_internal'] = True
        return permission_ref

    def _create_permission(self, permission_ref=None):
        if not permission_ref:
            permission_ref = self.new_fiware_permission_ref(uuid.uuid4().hex)        
        response = self.post(self.PERMISSIONS_URL, body={'permission': permission_ref})

        return response.result['permission']

    def _create_user(self):
        # To simulate the IdM's registration we also create a project with 
        # the same name as the user and give it membership status
        user_ref = self.new_user_ref(domain_id=test_v3.DEFAULT_DOMAIN_ID)

        project = self._create_organization(name=user_ref['name'])
        user_ref['default_project_id'] = project['id']
        
        user = self.identity_api.create_user(user_ref)
        user['password'] = user_ref['password']
        
        keystone_role = self._create_keystone_role()
        self._add_user_to_organization(
                        project_id=project['id'], 
                        user_id=user['id'],
                        keystone_role_id=keystone_role['id'])
        return user, project

    def _create_organization(self, name=None):
        # create a keystone project/fiware organization
        project_ref = self.new_project_ref(domain_id=test_v3.DEFAULT_DOMAIN_ID)
        project_ref['id'] = uuid.uuid4().hex
        if name:
            project_ref['name'] = name
        project = self.assignment_api.create_project(project_ref['id'], project_ref)
        return project

    def _create_keystone_role(self):
        keystone_role_ref = self.new_role_ref()
        keystone_role_ref['id'] = uuid.uuid4().hex
        keystone_role_ref['name'] = 'keystone_role_%s' % keystone_role_ref['id']
        keystone_role = self.assignment_api.create_role(keystone_role_ref['id'], 
                                                        keystone_role_ref)
        return keystone_role

    def _add_permission_to_role(self, role_id, permission_id, 
                                expected_status=204):    
        url_args = {
            'role_id':role_id,
            'permission_id':permission_id
        }
        url = self.ROLES_URL + '/%(role_id)s/permissions/%(permission_id)s' \
                                %url_args
        return self.put(url, expected_status=expected_status)


    def _add_user_to_organization(self, project_id, user_id, keystone_role_id):
        self.assignment_api.add_role_to_user_and_project(
            user_id, project_id, keystone_role_id)

    # ROLE-USERS
    def _list_role_user_assignments(self, filters=None, expected_status=200):
        url = self.USER_ASSIGNMENTS_URL
        if filters:
            query_string = urlencode(filters)
            url += '?' + query_string
        response = self.get(url, expected_status=expected_status)
        return response.result['role_assignments']

    def _add_role_to_user(self, role_id, user_id, 
                          organization_id, application_id, 
                          expected_status=204):
        url_args = {
            'role_id': role_id,
            'user_id': user_id,
            'organization_id': organization_id,
            'application_id': application_id,
        }
        url = self.USER_ROLES_URL.format(**url_args)
        return self.put(url, expected_status=expected_status)

    def _add_role_to_user_default_org(self, role_id, user_id, 
                                      application_id, 
                                      expected_status=204):
        url_args = {
            'role_id': role_id,
            'user_id': user_id,
            'application_id': application_id,
        }
        url = self.USER_DEFAULT_ORG_ROLES_URL.format(**url_args)
        return self.put(url, expected_status=expected_status)

    def _add_multiple_roles_to_user(self, number_of_roles, user_id, 
                                    organization_id, application_id):
        user_roles = []
        for i in range(number_of_roles):
            user_roles.append(self._create_role())
            self._add_role_to_user(role_id=user_roles[i]['id'], 
                                   user_id=user_id,
                                   organization_id=organization_id,
                                   application_id=application_id)

        return user_roles

    def _remove_role_from_user(self, role_id, user_id, 
                               organization_id, application_id,
                               expected_status=204):
        url_args = {
            'role_id': role_id,
            'user_id': user_id,
            'organization_id': organization_id,
            'application_id': application_id,
        }
        url = self.USER_ROLES_URL.format(**url_args)
        return self.delete(url, expected_status=expected_status)

    def _remove_role_from_user_default_org(self, role_id, user_id, 
                                           application_id,
                                           expected_status=204):
        url_args = {
            'role_id': role_id,
            'user_id': user_id,
            'application_id': application_id,
        }
        url = self.USER_DEFAULT_ORG_ROLES_URL.format(**url_args)
        return self.delete(url, expected_status=expected_status)

    # ROLES-ORGANIZATIONS
    def _list_role_organization_assignments(self, filters=None, expected_status=200):
        url = self.ORGANIZATION_ASSIGNMENTS_URL
        if filters:
            query_string = urlencode(filters)
            url += '?' + query_string
        response = self.get(url, expected_status=expected_status)
        return response.result['role_assignments']

    def _add_role_to_organization(self, role_id, 
                                  organization_id, application_id, 
                                  expected_status=204):
        url_args = {
            'role_id': role_id,
            'organization_id': organization_id,
            'application_id': application_id,
        }
        url = self.ORGANIZATION_ROLES_URL.format(**url_args)
        return self.put(url, expected_status=expected_status)

    def _add_multiple_roles_to_organization(self, number_of_roles, 
                                            organization_id, application_id):
        organization_roles = []
        for i in range(number_of_roles):
            organization_roles.append(self._create_role())
            self._add_role_to_organization(role_id=organization_roles[i]['id'], 
                                           organization_id=organization_id,
                                           application_id=application_id)

        return organization_roles

    def _remove_role_from_organization(self, role_id,
                                       organization_id, application_id,
                                       expected_status=204):
        url_args = {
            'role_id': role_id,
            'organization_id': organization_id,
            'application_id': application_id,
        }
        url = self.ORGANIZATION_ROLES_URL.format(**url_args)
        return self.delete(url, expected_status=expected_status)

    def _delete_role(self, role_id, expected_status=204):

        url_args = {
            'role_id': role_id,
        }
        url = self.ROLES_URL + '/%(role_id)s' \
                %url_args
        return self.delete(url, expected_status=expected_status)

    def _delete_permission(self, permission_id, expected_status=204):

        url_args = {
            'permission_id': permission_id,
        }
        url = self.PERMISSIONS_URL + '/%(permission_id)s' \
                    %url_args
        return self.delete(url, expected_status=expected_status)

    def _remove_permission_from_role(self, role_id, permission_id, expected_status=204):
        url_args = {
            'role_id':role_id,
            'permission_id':permission_id
        } 
        url = self.ROLES_URL + '/%(role_id)s/permissions/%(permission_id)s' \
                                %url_args
        return self.delete(url, expected_status=expected_status)

    # ALLOWED ACTIONS
    def _list_roles_user_allowed_to_assign(self, user_id, organization_id, 
                                           expected_status=200):
        url_args = {
            'user_id': user_id,
            'organization_id': organization_id
        }   
        url = self.USER_ALLOWED_ROLES_URL.format(**url_args)
        return self.get(url, expected_status=expected_status)

    def _list_roles_organization_allowed_to_assign(self, organization_id, 
                                                   expected_status=200):
        url_args = {
            'organization_id': organization_id
        }   
        url = self.ORGANIZATION_ALLOWED_ROLES_URL.format(**url_args)
        return self.get(url, expected_status=expected_status)

    def _list_applications_user_allowed_to_manage(self, user_id, organization_id, 
                                                  expected_status=200):
        url_args = {
            'user_id': user_id,
            'organization_id': organization_id
        }   
        url = self.USER_ALLOWED_APPLICATIONS_URL.format(**url_args)
        return self.get(url, expected_status=expected_status)

    def _list_applications_organization_allowed_to_manage(self, organization_id, 
                                                          expected_status=200):
        url_args = {
            'organization_id': organization_id
        }   
        url = self.ORGANIZATION_ALLOWED_APPLICATIONS_URL.format(**url_args)
        return self.get(url, expected_status=expected_status)

    def _list_applications_user_allowed_to_manage_roles(self, user_id, organization_id, 
                                                  expected_status=200):
        url_args = {
            'user_id': user_id,
            'organization_id': organization_id
        }   
        url = self.USER_ALLOWED_MANAGE_ROLES_URL.format(**url_args)
        return self.get(url, expected_status=expected_status)

    def _list_applications_organization_allowed_to_manage_roles(self, organization_id, 
                                                          expected_status=200):
        url_args = {
            'organization_id': organization_id
        }   
        url = self.ORGANIZATION_ALLOWED_MANAGE_ROLES_URL.format(**url_args)
        return self.get(url, expected_status=expected_status)

    def _assert_role(self, test_role, reference_role):
        self.assertIsNotNone(test_role)
        self.assertIsNotNone(test_role['id'])
        self.assertEqual(reference_role['name'], test_role['name'])
        if hasattr(reference_role, 'is_internal'):
            self.assertEqual(reference_role['is_internal'], test_role['is_internal'])

    def _assert_permission(self, test_permission, reference_permission):
        self.assertIsNotNone(test_permission)
        self.assertIsNotNone(test_permission['id'])
        self.assertEqual(reference_permission['name'], test_permission['name'])
        if hasattr(reference_permission, 'is_internal'):
            self.assertEqual(reference_permission['is_internal'], test_permission['is_internal'])

    def _create_consumer(self, name=None, description=None,
                         client_type='confidential',
                         redirect_uris=DEFAULT_REDIRECT_URIS,
                         grant_type='authorization_code',
                         scopes=DEFAULT_SCOPES,
                         **kwargs):
        if not name:
            name = uuid.uuid4().hex
        data = {
            'name': name,
            'description': description,
            'client_type': client_type,
            'redirect_uris': redirect_uris,
            'grant_type': grant_type,
            'scopes': scopes
        }
        # extra
        data.update(kwargs)
        response = self.post(self.CONSUMER_URL, body={'consumer': data})

        return response.result['consumer'], data


class RoleCrudTests(RolesBaseTests):

    def test_role_create_default(self):
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex)
        role = self._create_role(role_ref)

        self._assert_role(role, role_ref)

    def test_role_create_explicit(self):
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex, is_internal=True)
        role = self._create_role(role_ref)

        self._assert_role(role, role_ref)

    def test_role_create_not_editable(self):
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex, is_internal=False)
        role = self._create_role(role_ref)

        self._assert_role(role, role_ref)

    def test_roles_list(self):
        application = uuid.uuid4().hex
        role_ref1 = self.new_fiware_role_ref(uuid.uuid4().hex, 
                                             application=application)
        role1 = self._create_role(role_ref1)

        role_ref2 = self.new_fiware_role_ref(uuid.uuid4().hex, 
                                             application=uuid.uuid4().hex)
        role2 = self._create_role(role_ref2)
        response = self.get(self.ROLES_URL + 
            '?application_id={0}'.format(application))
        entities = response.result['roles']
        self.assertIsNotNone(entities)

        self_url = ''.join(['http://localhost/v3', 
            self.ROLES_URL, '?application_id={0}'.format(application)])
        self.assertEqual(response.result['links']['self'], self_url)
        self.assertValidListLinks(response.result['links'])

        self.assertEqual(1, len(entities))

    def test_roles_list_filter_by_application(self):
        role1 = self._create_role()
        role2 = self._create_role()
        response = self.get(self.ROLES_URL)
        entities = response.result['roles']
        self.assertIsNotNone(entities)

        self_url = ''.join(['http://localhost/v3', self.ROLES_URL])
        self.assertEqual(response.result['links']['self'], self_url)
        self.assertValidListLinks(response.result['links'])

        self.assertEqual(2, len(entities))

    def test_get_role(self):
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex)
        role = self._create_role(role_ref)
        role_id = role['id']
        response = self.get(self.ROLES_URL + '/%s' %role_id)
        get_role = response.result['role']

        self._assert_role(role, role_ref)
        self_url = ['http://localhost/v3', self.ROLES_URL, '/', role_id]
        self_url = ''.join(self_url)
        self.assertEqual(self_url, get_role['links']['self'])
        self.assertEqual(role_id, get_role['id'])

    def test_update_role(self):
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex)
        role = self._create_role(role_ref)
        original_id = role['id']
        update_name = role['name'] + '_new'
        role_ref['name'] = update_name
        body = {
            'role': {
                'name': update_name,
            }
        }
        response = self.patch(self.ROLES_URL + '/%s' %original_id,
                                 body=body)
        update_role = response.result['role']

        self._assert_role(update_role, role_ref)
        self.assertEqual(original_id, update_role['id'])

    def test_delete_role(self):
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex)
        role = self._create_role(role_ref)
        role_id = role['id']
        response = self._delete_role(role_id)


class RoleUserAssignmentTests(RolesBaseTests):

    def test_list_role_user_assignments_no_filters(self):
        number_of_users = 2
        number_of_roles = 2
        references = []
        for i in range(number_of_users):
            application_id = uuid.uuid4().hex
            user, organization = self._create_user()
            
            user_roles = self._add_multiple_roles_to_user(number_of_roles, 
                         user['id'], organization['id'], application_id)
            references.append((user, organization, application_id, user_roles))

        assignments = self._list_role_user_assignments()

        self.assertEqual(number_of_roles * number_of_users, len(assignments))
        for (user, organization, application_id, user_roles) in references:
            current_assignments = [a['role_id'] for a in assignments 
                                     if a['user_id'] == user['id']
                                     and a['organization_id'] == organization['id']
                                     and a['application_id'] == application_id]
            current_roles = [r['id'] for r in user_roles]                         
            self.assertEqual(current_roles, current_assignments)

    def test_list_users_with_roles_in_application(self):
        number_of_users = 2
        number_of_roles = 2
        references = []
        
        for i in range(number_of_users):
            application_id = uuid.uuid4().hex
            user, organization = self._create_user()
            
            user_roles = self._add_multiple_roles_to_user(number_of_roles, 
                         user['id'], organization['id'], application_id)
            references.append((user, organization, application_id, user_roles))

        app_to_filter = references[0][2]
        assignments = self._list_role_user_assignments(
            filters={'application_id':app_to_filter})

        self.assertEqual(number_of_roles, len(assignments))
        self.assertEqual(set([app_to_filter]), 
                         set([a['application_id'] for a in assignments]))

        # filter references
        references = [r for r in references if r[2] == app_to_filter]
        for (user, organization, application_id, user_roles) in references:
            current_assignments = [a['role_id'] for a in assignments 
                                     if a['user_id'] == user['id']
                                     and a['organization_id'] == organization['id']
                                     and a['application_id'] == application_id]
            current_roles = [r['id'] for r in user_roles]                         
            self.assertEqual(current_roles, current_assignments)

    def test_list_applications_where_user_has_roles(self):
        number_of_users = 2
        number_of_roles = 2
        references = []
        
        for i in range(number_of_users):
            application_id = uuid.uuid4().hex
            user, organization = self._create_user()
            
            user_roles = self._add_multiple_roles_to_user(number_of_roles, 
                         user['id'], organization['id'], application_id)
            references.append((user, organization, application_id, user_roles))

        user_to_filter = references[0][0]['id']
        assignments = self._list_role_user_assignments(
            filters={'user_id':user_to_filter})

        self.assertEqual(number_of_roles, len(assignments))
        self.assertEqual(set([user_to_filter]), 
                         set([a['user_id'] for a in assignments]))

        # filter references
        references = [r for r in references if r[0]['id'] == user_to_filter]
        for (user, organization, application_id, user_roles) in references:
            current_assignments = [a['role_id'] for a in assignments 
                                     if a['user_id'] == user['id']
                                     and a['organization_id'] == organization['id']
                                     and a['application_id'] == application_id]
            current_roles = [r['id'] for r in user_roles]                         
            self.assertEqual(current_roles, current_assignments)

    def test_list_all_users_from_organization_with_roles(self):
        number_of_users = 2
        number_of_roles = 2
        references = []
        
        for i in range(number_of_users):
            application_id = uuid.uuid4().hex
            user, organization = self._create_user()
            
            user_roles = self._add_multiple_roles_to_user(number_of_roles, 
                         user['id'], organization['id'], application_id)
            references.append((user, organization, application_id, user_roles))

        organization_to_filter = references[0][1]['id']
        assignments = self._list_role_user_assignments(
            filters={'organization_id':organization_to_filter})

        self.assertEqual(number_of_roles, len(assignments))
        self.assertEqual(set([organization_to_filter]), 
                         set([a['organization_id'] for a in assignments]))

        # filter references
        references = [r for r in references if r[1]['id'] == organization_to_filter]
        for (user, organization, application_id, user_roles) in references:
            current_assignments = [a['role_id'] for a in assignments 
                                     if a['user_id'] == user['id']
                                     and a['organization_id'] == organization['id']
                                     and a['application_id'] == application_id]
            current_roles = [r['id'] for r in user_roles]                         
            self.assertEqual(current_roles, current_assignments)


    def test_add_role_to_user(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        user, organization = self._create_user()
        response = self._add_role_to_user(role_id=role['id'],
                                          user_id=user['id'],
                                          organization_id=organization['id'],
                                          application_id=application)

    def test_add_non_existent_role_to_user(self):
        application = uuid.uuid4().hex
        user, organization = self._create_user()
        response = self._add_role_to_user(role_id=uuid.uuid4().hex,
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application,
                                        expected_status=404)

    def test_add_role_to_non_existent_user(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        response = self._add_role_to_user(role_id=role['id'],
                                        user_id=uuid.uuid4().hex,
                                        organization_id=uuid.uuid4().hex,
                                        application_id=application,
                                        expected_status=404)

    def test_add_role_to_user_repeated(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        user, organization = self._create_user()
        response = self._add_role_to_user(role_id=role['id'],
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._add_role_to_user(role_id=role['id'],
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application)

    def test_add_role_to_user_default_org(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        user, organization = self._create_user()
        response = self._add_role_to_user_default_org(
            role_id=role['id'],
            user_id=user['id'],
            application_id=application)

    def test_remove_role_from_user(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        user, organization = self._create_user()
        response = self._add_role_to_user(role_id=role['id'],
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._remove_role_from_user(role_id=role['id'],
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application)

    def test_remove_non_existent_role_from_user(self):
        application = uuid.uuid4().hex
        user, organization = self._create_user()
        response = self._remove_role_from_user(role_id=uuid.uuid4().hex,
                                            user_id=user['id'],
                                            organization_id=organization['id'],
                                            application_id=application,
                                            expected_status=404)

    def test_remove_role_from_non_existent_user(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        response = self._remove_role_from_user(role_id=role['id'],
                                            user_id=uuid.uuid4().hex,
                                            organization_id=uuid.uuid4().hex,
                                            application_id=application,
                                            expected_status=404)

    def test_remove_user_from_role_repeated(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        user, organization = self._create_user()
        response = self._add_role_to_user(role_id=role['id'],
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._remove_role_from_user(role_id=role['id'],
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._remove_role_from_user(role_id=role['id'],
                                        user_id=user['id'],
                                        organization_id=organization['id'],
                                        application_id=application)

    def test_remove_role_from_user_default_org(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        user, organization = self._create_user()
        response = self._add_role_to_user_default_org(
            role_id=role['id'],
            user_id=user['id'],
            application_id=application)
        response = self._remove_role_from_user_default_org(
            role_id=role['id'],
            user_id=user['id'],
            application_id=application)
class RoleOrganizationAssignmentTests(RolesBaseTests):

    def test_list_role_organization_assignments_no_filters(self):
        number_of_organizations = 2
        number_of_roles = 2
        references = []
        for i in range(number_of_organizations):
            application_id = uuid.uuid4().hex
            organization = self._create_organization()
            
            organization_roles = self._add_multiple_roles_to_organization(
                number_of_roles, organization['id'], application_id)
            references.append((organization, application_id, organization_roles))

        assignments = self._list_role_organization_assignments()

        self.assertEqual(number_of_roles * number_of_organizations, len(assignments))
        for (organization, application_id, organization_roles) in references:
            current_assignments = [a['role_id'] for a in assignments 
                                     if a['organization_id'] == organization['id']
                                     and a['application_id'] == application_id]
            current_roles = [r['id'] for r in organization_roles]                         
            self.assertEqual(current_roles, current_assignments)

    def test_list_organizations_with_roles_in_application(self):
        number_of_organizations = 2
        number_of_roles = 2
        references = []
        
        for i in range(number_of_organizations):
            application_id = uuid.uuid4().hex
            organization = self._create_organization()
            
            organization_roles = self._add_multiple_roles_to_organization(
                number_of_roles, organization['id'], application_id)
            references.append((organization, application_id, organization_roles))

        app_to_filter = references[0][1]
        assignments = self._list_role_organization_assignments(
            filters={'application_id':app_to_filter})

        self.assertEqual(number_of_roles, len(assignments))
        self.assertEqual(set([app_to_filter]), 
                         set([a['application_id'] for a in assignments]))

        # filter references
        references = [r for r in references if r[1] == app_to_filter]
        for (organization, application_id, organization_roles) in references:
            current_assignments = [a['role_id'] for a in assignments 
                                     if a['organization_id'] == organization['id']
                                     and a['application_id'] == application_id]
            current_roles = [r['id'] for r in organization_roles]                         
            self.assertEqual(current_roles, current_assignments)


    def test_list_applications_where_organization_has_roles(self):
        number_of_organizations = 2
        number_of_roles = 2
        references = []
        
        for i in range(number_of_organizations):
            application_id = uuid.uuid4().hex
            organization = self._create_organization()
            organization_roles = self._add_multiple_roles_to_organization(
                number_of_roles, organization['id'], application_id)
            references.append((organization, application_id, organization_roles))

        organization_to_filter = references[0][0]['id']
        assignments = self._list_role_organization_assignments(
            filters={'organization_id':organization_to_filter})

        self.assertEqual(number_of_roles, len(assignments))
        self.assertEqual(set([organization_to_filter]), 
                         set([a['organization_id'] for a in assignments]))

        # filter references
        references = [r for r in references if r[0]['id'] == organization_to_filter]
        for (organization, application_id, organization_roles) in references:
            current_assignments = [a['role_id'] for a in assignments
                                   if a['organization_id'] == organization['id']
                                   and a['application_id'] == application_id]
            current_roles = [r['id'] for r in organization_roles]                    
            self.assertEqual(current_roles, current_assignments)

    def test_add_role_to_organization(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        organization = self._create_organization()
        response = self._add_role_to_organization(role_id=role['id'],
                                          organization_id=organization['id'],
                                          application_id=application)

    def test_add_non_existent_role_to_organization(self):
        application = uuid.uuid4().hex
        organization = self._create_organization()
        response = self._add_role_to_organization(role_id=uuid.uuid4().hex,
                                        organization_id=organization['id'],
                                        application_id=application,
                                        expected_status=404)

    def test_add_role_to_non_existent_organization(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        response = self._add_role_to_organization(role_id=role['id'],
                                        organization_id=uuid.uuid4().hex,
                                        application_id=application,
                                        expected_status=404)

    def test_add_role_to_organization_repeated(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        organization = self._create_organization()
        response = self._add_role_to_organization(role_id=role['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._add_role_to_organization(role_id=role['id'],
                                        organization_id=organization['id'],
                                        application_id=application)

    def test_remove_role_from_organization(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        organization = self._create_organization()
        response = self._add_role_to_organization(role_id=role['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._remove_role_from_organization(role_id=role['id'],
                                        organization_id=organization['id'],
                                        application_id=application)

    def test_remove_non_existent_role_from_organization(self):
        application = uuid.uuid4().hex
        organization = self._create_organization()
        response = self._remove_role_from_organization(role_id=uuid.uuid4().hex,
                                            organization_id=organization['id'],
                                            application_id=application,
                                            expected_status=404)

    def test_remove_role_from_non_existent_organization(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        response = self._remove_role_from_organization(role_id=role['id'],
                                            organization_id=uuid.uuid4().hex,
                                            application_id=application,
                                            expected_status=404)

    def test_remove_organization_from_role_repeated(self):
        application = uuid.uuid4().hex
        role_ref = self.new_fiware_role_ref(uuid.uuid4().hex,
                                            application=application)
        role = self._create_role(role_ref)
        organization = self._create_organization()
        response = self._add_role_to_organization(role_id=role['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._remove_role_from_organization(role_id=role['id'],
                                        organization_id=organization['id'],
                                        application_id=application)
        response = self._remove_role_from_organization(role_id=role['id'],
                                        organization_id=organization['id'],
                                        application_id=application)

class InternalRolesTests(RolesBaseTests):
    # TODO(garcianavalon) refactor this for better reuse, really bad now
    # TODO(garcianavalon) create more tests with more complex and limit cases

    def test_list_roles_user_allowed_to_assing_owned(self):
        user, organization = self._create_user()
        permission = core.ASSIGN_OWNED_PUBLIC_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        internal_roles, expected_roles = self._create_internal_roles_user(user, 
                                                organization, 
                                                permission,
                                                app_id)

        response = self._list_roles_user_allowed_to_assign(user_id=user['id'],
                                          organization_id=organization['id'])
        # check the correct roles are returned
        allowed_roles = json.loads(response.body)['allowed_roles']
        for app in allowed_roles:
            self.assertEqual(app_id, app)
            current = [r_id for r_id in allowed_roles[app]]
            expected = [r_id for r_id in expected_roles
                                    if expected_roles[r_id]]   
            self.assertItemsEqual(current, expected)


    def test_list_roles_user_allowed_to_assign_all(self):
        user, organization = self._create_user()
        permission = core.ASSIGN_ALL_PUBLIC_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        internal_roles, expected_roles = self._create_internal_roles_user(user, 
                                                organization, 
                                                permission,
                                                app_id)

        response = self._list_roles_user_allowed_to_assign(user_id=user['id'],
                                          organization_id=organization['id'])
        # check the correct roles are returned
        allowed_roles = json.loads(response.body)['allowed_roles']
        for app in allowed_roles:
            self.assertEqual(app_id, app)
            current = [r_id for r_id in allowed_roles[app]]
            expected = expected_roles.keys() 
            self.assertItemsEqual(current, expected)

    def test_list_roles_user_allowed_to_assign_internal(self):
        user, organization = self._create_user()
        permission = core.ASSIGN_INTERNAL_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        internal_roles, expected_roles = self._create_internal_roles_user(user, 
                                                organization, 
                                                permission,
                                                app_id)

        response = self._list_roles_user_allowed_to_assign(user_id=user['id'],
                                          organization_id=organization['id'])
        # check the correct roles are returned
        allowed_roles = json.loads(response.body)['allowed_roles']
        for app in allowed_roles:
            self.assertEqual(app_id, app)
            current = [r_id for r_id in allowed_roles[app]]
            expected = [r['id'] for r in internal_roles]
            self.assertItemsEqual(current, expected)

    def test_list_roles_organization_allowed_to_assign_all(self):
        organization = self._create_organization()
        permission = core.ASSIGN_ALL_PUBLIC_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        internal_roles, expected_roles = self._create_internal_roles_organization(
            organization, permission, app_id)

        response = self._list_roles_organization_allowed_to_assign(
            organization_id=organization['id'])
        # check the correct roles are returned
        allowed_roles = json.loads(response.body)['allowed_roles']
        for app in allowed_roles:
            self.assertEqual(app_id, app)
            current = [r_id for r_id in allowed_roles[app]]
            expected = expected_roles.keys() 
            self.assertItemsEqual(current, expected)


    def test_list_roles_organization_allowed_to_assing_owned(self):
        organization = self._create_organization()
        permission = core.ASSIGN_OWNED_PUBLIC_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        internal_roles, expected_roles = self._create_internal_roles_organization(
            organization, permission, app_id)

        response = self._list_roles_organization_allowed_to_assign(
            organization_id=organization['id'])
        # check the correct roles are returned
        allowed_roles = json.loads(response.body)['allowed_roles']
        for app in allowed_roles:
            self.assertEqual(app_id, app)
            current = [r_id for r_id in allowed_roles[app]]
            expected = [r_id for r_id in expected_roles
                                    if expected_roles[r_id]]   
            self.assertItemsEqual(current, expected)
    
    def test_list_roles_organization_allowed_to_assign_internal(self):
        organization = self._create_organization()
        permission = core.ASSIGN_INTERNAL_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        internal_roles, expected_roles = self._create_internal_roles_organization(
            organization, permission, app_id)

        response = self._list_roles_organization_allowed_to_assign(
            organization_id=organization['id'])
        # check the correct roles are returned
        allowed_roles = json.loads(response.body)['allowed_roles']
        for app in allowed_roles:
            self.assertEqual(app_id, app)
            current = [r_id for r_id in allowed_roles[app]]
            expected = [r['id'] for r in internal_roles]
            self.assertItemsEqual(current, expected)

    def test_list_applications_user_allowed_to_manage(self):
        user, organization = self._create_user()
        permission = core.MANAGE_APPLICATION_PERMISSION
        app_id = uuid.uuid4().hex
        self._create_internal_roles_user(user, 
                                         organization, 
                                         permission,
                                         app_id)

        response = self._list_applications_user_allowed_to_manage(
            user_id=user['id'], organization_id=organization['id'])

        # check the correct applications are returned
        allowed_apps = json.loads(response.body)['allowed_applications']
        self.assertEqual([app_id], allowed_apps)

    def test_list_applications_organization_allowed_to_manage(self):
        organization = self._create_organization()
        permission = core.MANAGE_APPLICATION_PERMISSION
        app_id = uuid.uuid4().hex
        self._create_internal_roles_organization(
            organization, permission, app_id)

        response = self._list_applications_organization_allowed_to_manage(
            organization_id=organization['id'])

        # check the correct applications are returned
        allowed_apps = json.loads(response.body)['allowed_applications']
        self.assertEqual([app_id], allowed_apps)

    def test_list_applications_user_allowed_to_manage_roles(self):
        user, organization = self._create_user()
        permission = core.MANAGE_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        self._create_internal_roles_user(user, 
                                         organization, 
                                         permission,
                                         app_id)

        response = self._list_applications_user_allowed_to_manage_roles(
            user_id=user['id'], organization_id=organization['id'])

        # check the correct applications are returned
        allowed_apps = json.loads(response.body)['allowed_applications']
        self.assertEqual([app_id], allowed_apps)

    def test_list_applications_organization_allowed_to_manage_roles(self):
        organization = self._create_organization()
        permission = core.MANAGE_ROLES_PERMISSION
        app_id = uuid.uuid4().hex
        self._create_internal_roles_organization(
            organization, permission, app_id)

        response = self._list_applications_organization_allowed_to_manage_roles(
            organization_id=organization['id'])

        # check the correct applications are returned
        allowed_apps = json.loads(response.body)['allowed_applications']
        self.assertEqual([app_id], allowed_apps)

    def _create_internal_roles_user(self, user, organization, permission, app_id):
        internal_roles = []
        expected_roles = {}
        permissions = []
        
        # create the internal permissions
        perm_ref = self.new_fiware_permission_ref(
                                permission, 
                                application=app_id, 
                                is_internal=True)
        permissions.append(self._create_permission(perm_ref))

        # create the internal role
        role_ref = self.new_fiware_permission_ref(
                                uuid.uuid4().hex, 
                                application=app_id, 
                                is_internal=True)
        role = self._create_role(role_ref)
        internal_roles.append(role)

        # assign the permissions to the role
        for permission in permissions:
            self._add_permission_to_role(role['id'], permission['id'])
        expected_roles[role['id']] = permissions
        # grant the role to the user
        self._add_role_to_user(role['id'], 
                               user['id'], 
                               organization['id'], 
                               app_id)

        # now create another role in the app to test all vs owned
        another_role_ref = self.new_fiware_permission_ref(
                                uuid.uuid4().hex, 
                                application=app_id, 
                                is_internal=False)
        another_role = self._create_role(another_role_ref)
        expected_roles[another_role['id']] = []
        return internal_roles, expected_roles
                

    def _create_internal_roles_organization(self, organization, permission, app_id):
        internal_roles = []
        expected_roles = {}
        permissions = []
        
        # create the internal permissions
        perm_ref = self.new_fiware_permission_ref(
                                permission, 
                                application=app_id, 
                                is_internal=True)
        permissions.append(self._create_permission(perm_ref))

        # create the internal role
        role_ref = self.new_fiware_permission_ref(
                                uuid.uuid4().hex, 
                                application=app_id, 
                                is_internal=True)
        role = self._create_role(role_ref)
        internal_roles.append(role)

        # assign the permissions to the role
        for permission in permissions:
            self._add_permission_to_role(role['id'], permission['id'])
        expected_roles[role['id']] = permissions
        # grant the role to the user
        self._add_role_to_organization(role['id'], 
                               organization['id'], 
                               app_id)

        # now create another role in the app to test all vs owned
        another_role_ref = self.new_fiware_permission_ref(
                                uuid.uuid4().hex, 
                                application=app_id, 
                                is_internal=False)
        another_role = self._create_role(another_role_ref)
        expected_roles[another_role['id']] = []
        return internal_roles, expected_roles


class PermissionCrudTests(RolesBaseTests):

    def test_create_permission_default(self):
        permission_ref = self.new_fiware_permission_ref(uuid.uuid4().hex)
        permission = self._create_permission(permission_ref)

        self._assert_permission(permission, permission_ref)

    def test_create_permission_explicit(self):
        permission_ref = self.new_fiware_permission_ref(uuid.uuid4().hex, is_internal=True)
        permission = self._create_permission(permission_ref)

        self._assert_permission(permission, permission_ref)

    def test_create_permission_not_editable(self):
        permission_ref = self.new_fiware_permission_ref(uuid.uuid4().hex, is_internal=False)
        permission = self._create_permission(permission_ref)

        self._assert_permission(permission, permission_ref)

    def test_list_permissions(self):
        permission1 = self._create_permission()
        permission2 = self._create_permission()

        response = self.get(self.PERMISSIONS_URL)
        entities = response.result['permissions']

        self.assertIsNotNone(entities)

        self_url = ['http://localhost/v3', self.PERMISSIONS_URL]
        self_url = ''.join(self_url)
        self.assertEqual(response.result['links']['self'], self_url)
        self.assertValidListLinks(response.result['links'])

        self.assertEqual(2, len(entities))

    def test_get_permission(self):
        permission_ref = self.new_fiware_permission_ref(uuid.uuid4().hex)
        permission = self._create_permission(permission_ref)
        permission_id = permission['id']
        response = self.get(self.PERMISSIONS_URL + '/%s' %permission_id)
        get_permission = response.result['permission']

        self._assert_permission(permission, permission_ref)
        self_url = ['http://localhost/v3', self.PERMISSIONS_URL, '/', permission_id]
        self_url = ''.join(self_url)
        self.assertEqual(self_url, get_permission['links']['self'])
        self.assertEqual(permission_id, get_permission['id'])

    def test_update_permission(self):
        permission_ref = self.new_fiware_permission_ref(uuid.uuid4().hex)
        permission = self._create_permission(permission_ref)
        original_id = permission['id']
        original_name = permission['name']
        update_name = original_name + '_new'
        permission_ref['name'] = update_name
        body = {
            'permission': {
                'name': update_name,
            }
        }
        response = self.patch(self.PERMISSIONS_URL + '/%s' %original_id,
                                 body=body)
        update_permission = response.result['permission']

        self._assert_permission(update_permission, permission_ref)
        self.assertEqual(original_id, update_permission['id'])

    def test_delete_permission(self):
        permission = self._create_permission()
        permission_id = permission['id']
        response = self._delete_permission(permission_id)

    def test_list_permissions_for_role(self):
        role = self._create_role()
        permission = self._create_permission()

        self._add_permission_to_role(role_id=role['id'], 
                                     permission_id=permission['id'])

        url_args = {
            'role_id':role['id']
        }   
        url = self.ROLES_URL + '/%(role_id)s/permissions/' \
                                %url_args

        response = self.get(url)
        entities = response.result['permissions']

        self.assertIsNotNone(entities)

        self.assertEqual(1, len(entities))

    def test_add_permission_to_role(self):
        role = self._create_role()
        permission = self._create_permission()
        response = self._add_permission_to_role(role_id=role['id'], 
                                                permission_id=permission['id'])

    def test_add_permission_to_role_non_existent(self):
        permission = self._create_permission()
        response = self._add_permission_to_role(role_id=uuid.uuid4().hex, 
                                                permission_id=permission['id'],
                                                expected_status=404)

    def test_add_non_existent_permission_to_role(self):
        role = self._create_role()
        response = self._add_permission_to_role(role_id=role['id'], 
                                                permission_id=uuid.uuid4().hex,
                                                expected_status=404)

    def test_add_permission_to_role_repeated(self):
        role = self._create_role()
        permission = self._create_permission()
        response = self._add_permission_to_role(role_id=role['id'], 
                                                permission_id=permission['id'])
        response = self._add_permission_to_role(role_id=role['id'], 
                                                permission_id=permission['id'])

    def test_remove_permission_from_role(self):
        role = self._create_role()
        permission = self._create_permission()

        response = self._add_permission_to_role(role_id=role['id'], 
                                                permission_id=permission['id'])

        response = self._remove_permission_from_role(role_id=role['id'], 
                                                     permission_id=permission['id'])

    def test_remove_permission_from_role_non_associated(self):
        role = self._create_role()
        permission = self._create_permission()
        
        response = self._remove_permission_from_role(role_id=role['id'], 
                                                     permission_id=permission['id'])

    def test_remove_permission_from_non_existent_role(self):
        permission = self._create_permission()

        response = self._remove_permission_from_role(role_id=uuid.uuid4().hex, 
                                                     permission_id=permission['id'],
                                                     expected_status=404)

    def test_remove_non_existent_permission_from_role(self):
        role = self._create_role()

        response = self._remove_permission_from_role(role_id=role['id'], 
                                                     permission_id=uuid.uuid4().hex,
                                                     expected_status=404)

    def test_remove_permision_from_role_repeated(self):
        role = self._create_role()
        permission = self._create_permission()

        response = self._add_permission_to_role(role_id=role['id'], 
                                                permission_id=permission['id'])

        response = self._remove_permission_from_role(role_id=role['id'], 
                                                     permission_id=permission['id'])
        response = self._remove_permission_from_role(role_id=role['id'], 
                                                     permission_id=permission['id'])

@dependency.requires('oauth2_api')
class FiwareApiTests(RolesBaseTests):
    number_of_organizations = 0
    number_of_user_roles = 0
    number_of_organization_roles = 0

    def setUp(self):
        super(FiwareApiTests, self).setUp()
        # create user
        self.test_user, self.user_organization = self._create_user()

        # create a keystone role
        self.keystone_role = self._create_keystone_role()

        # create an application
        consumer, data = self._create_consumer()
        self.application_id = consumer['id']

    def _create_organizations_with_user_and_keystone_role(self):
        organizations = []
        for i in range(self.number_of_organizations):
            organizations.append(self._create_organization())
            self._add_user_to_organization(
                        project_id=organizations[i]['id'], 
                        user_id=self.test_user['id'],
                        keystone_role_id=self.keystone_role['id'])
        self.organizations = organizations

    def _assign_user_scoped_roles(self):
        user_roles = []
        for i in range(self.number_of_user_roles):
            role = self._create_role(self.new_fiware_role_ref(self.application_id))
            user_roles.append(role)
            self._add_role_to_user(role_id=user_roles[i]['id'], 
                                   user_id=self.test_user['id'],
                                   organization_id=self.user_organization['id'],
                                   application_id=self.application_id)
        self.user_roles = user_roles

    def _assign_organization_scoped_roles(self):
        organization_roles = {}
        for organization in self.organizations:
            organization_roles[organization['name']] = []
            for i in range(self.number_of_organization_roles):
                role = self._create_role(self.new_fiware_role_ref(self.application_id))
                organization_roles[organization['name']].append(role)
                role = organization_roles[organization['name']][i]
                self._add_role_to_user(role_id=role['id'], 
                                    user_id=self.test_user['id'],
                                    organization_id=organization['id'],
                                    application_id=self.application_id)
        self.organization_roles = organization_roles

    def _create_oauth2_token(self):
        token_dict = {
            'id':uuid.uuid4().hex,
            'consumer_id':self.application_id,
            'authorizing_user_id':self.test_user['id'],
            'scopes': [uuid.uuid4().hex],
            'expires_at':uuid.uuid4().hex,
        }
        oauth2_access_token = self.oauth2_api.store_access_token(token_dict)
        return oauth2_access_token['id']

    def _validate_token(self, token_id):
        url = '/access-tokens/%s' %token_id
        return self.get(url)

    def _authorized_organizations(self, token_id):
        url = '/authorized_organizations/%s' %token_id
        return self.get(url)

    def _assert_user_info(self):
        result = self.response.result
        self.assertEqual(self.test_user['id'], result['id'])
        self.assertIsNotNone(result['email'])
        self.assertEqual(self.test_user['name'], result['displayName'])
        self.assertEqual(self.application_id, result['app_id'])

    def _assert_user_scoped_roles(self):
        response_user_roles = self.response.result['roles']
        self.assertIsNotNone(response_user_roles)

        for role in response_user_roles:
            self.assertIsNotNone(role['id'])
            self.assertIsNotNone(role['name'])

        actual_user_roles = set([role['id'] for role in response_user_roles])
        if self.number_of_user_roles:
            expected_user_roles = set([role['id'] for role in self.user_roles])
        else:
            expected_user_roles = set([])
        self.assertEqual(actual_user_roles, expected_user_roles)
    
    def _assert_organization_scoped_roles(self):
        response_organizations = self.response.result['organizations']
        self.assertIsNotNone(response_organizations)

        expected_orgs = (self.number_of_organizations 
            if self.number_of_organization_roles else 0)
        self.assertEqual(expected_orgs, len(response_organizations))

        for organization in response_organizations:
            self.assertIsNotNone(organization['id'])
            self.assertIsNotNone(organization['name'])
            self.assertIsNotNone(organization['roles'])

            for role in organization['roles']:
                self.assertIsNotNone(role['id'])
                self.assertIsNotNone(role['name'])

            actual_org_roles = set([role['id'] for role in organization['roles']])
            
            if self.number_of_organization_roles:
                expected_org_roles = set([role['id'] for role 
                    in self.organization_roles[organization['name']]])
            else:
                expected_org_roles = set([])
            self.assertEqual(expected_org_roles, actual_org_roles)

    def _create_all(self):
        # create some projects/organizations
        self._create_organizations_with_user_and_keystone_role()

        # assign some user-scoped roles
        self._assign_user_scoped_roles()

        # assign some organization-scoped roles
        self._assign_organization_scoped_roles()

    def _assert_all(self):
        self._assert_user_info()
        self._assert_user_scoped_roles()
        self._assert_organization_scoped_roles()

    def test_validate_token_basic(self):
        self.number_of_organizations = 2
        self.number_of_user_roles = 2
        self.number_of_organization_roles = 1
        self._create_all()
        # get a token for the user
        token_id = self._create_oauth2_token()
        # access the resource
        self.response = self._validate_token(token_id)
        self._assert_all()

    def test_validate_token_no_organizations(self):
        self.number_of_user_roles = 2
        self._create_all()
        # get a token for the user
        token_id = self._create_oauth2_token()
        # access the resource
        self.response = self._validate_token(token_id)
        self._assert_all()
        
    def test_validate_token_no_user_scoped_roles(self):
        self.number_of_organizations = 2
        self.number_of_organization_roles = 1
        self._create_all()
        # get a token for the user
        token_id = self._create_oauth2_token()
        # access the resource
        self.response = self._validate_token(token_id)
        self._assert_all()

    def test_validate_token_no_organization_scoped_roles(self):
        self.number_of_organizations = 2
        self.number_of_user_roles = 2
        self._create_all()
        # get a token for the user
        token_id = self._create_oauth2_token()
        # access the resource
        self.response = self._validate_token(token_id)
        self._assert_all()

    def test_validate_token_no_roles(self):
        self.number_of_organizations = 2
        self._create_all()
        # get a token for the user
        token_id = self._create_oauth2_token()
        # access the resource
        self.response = self._validate_token(token_id)
        self._assert_all()

    def test_validate_token_empty_user(self):
        self._create_all()
        # get a token for the user
        token_id = self._create_oauth2_token()
        # access the resource
        self.response = self._validate_token(token_id)
        self._assert_all()

    def test_authorized_organizations(self):
        self.number_of_organizations = 2
        self.number_of_user_roles = 2
        self.number_of_organization_roles = 1
        self._create_all()
        # get a token for the user
        token_id = self._create_oauth2_token()
        # access the resource
        self.response = self._authorized_organizations(token_id)
        
        response_organizations = self.response.result['organizations']
        
        # check default org is NOT there
        user_organization = next((org for org in response_organizations 
            if org['id'] == self.user_organization['id']), None)
        self.assertIsNone(user_organization)

        # check the others are
        expected_orgs = (self.number_of_organizations)
        self.assertEqual(expected_orgs, len(response_organizations))

class ExtendedPermissionsConsumerCRUDTests(test_v3_oauth2.ConsumerCRUDTests):
    EXTENSION_NAME = 'roles'
    EXTENSION_TO_ADD = 'roles_extension'

    PATH_PREFIX = '/OS-ROLES'
    CONSUMER_URL = PATH_PREFIX + '/consumers'
    USERS_URL = '/users/{user_id}'
    ACCESS_TOKENS_URL = PATH_PREFIX + '/access_tokens'

    def setUp(self):
        super(ExtendedPermissionsConsumerCRUDTests, self).setUp()

        # Now that the app has been served, we can query CONF values
        self.base_url = 'http://localhost/v3'
        # NOTE(garcianavalon) I've put this line for dependency injection to work, 
        # but I don't know if its the right way to do it...
        self.manager = core.RolesManager()