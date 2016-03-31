# Copyright (C) 2015 Universidad Politecnica de Madrid
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
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

import sqlalchemy as sql
from migrate.changeset.constraint import ForeignKeyConstraint


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    authorization_code_table = sql.Table('authorization_code_oauth2', meta, autoload=True)
    consumer_oauth2 = sql.Table('consumer_oauth2', meta, autoload=True)

    if 'mysql' in str(meta):
        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_ibfk_1').drop()

        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_ibfk_1', ondelete='CASCADE').create()

    elif 'postgres' in str(meta):
        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_consumer_id_fkey').drop()

        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_consumer_id_fkey', ondelete='CASCADE').create()

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = sql.MetaData()
    meta.bind = migrate_engine

    authorization_code_table = sql.Table('authorization_code_oauth2', meta, autoload=True)
    consumer_oauth2 = sql.Table('consumer_oauth2', meta, autoload=True)

    if 'mysql' in str(meta):
        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_ibfk_1', ondelete='CASCADE').drop()

        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_ibfk_1').create()

    elif 'postgres' in str(meta):
        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_consumer_id_fkey', ondelete='CASCADE').drop()

        ForeignKeyConstraint(
            columns=[authorization_code_table.c.consumer_id],
            refcolumns=[consumer_oauth2.c.id],
            name='authorization_code_oauth2_consumer_id_fkey').create()
