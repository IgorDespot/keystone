# Copyright (C) 2015 Universidad Politecnica de Madrid
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


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    two_factor_auth_table = sql.Table(
        'two_factor_auth',
        meta,
        sql.Column('user_id', sql.String(64), nullable=False, primary_key=True),
        sql.Column('two_factor_key', sql.String(32), nullable=False),
        sql.Column('security_question', sql.String(128), nullable=False),
        sql.Column('security_answer', sql.String(128), nullable=False))
    two_factor_auth_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = sql.MetaData()
    meta.bind = migrate_engine

    two_factor_auth_table = sql.Table('two_factor_auth', meta, autoload=True)
    two_factor_auth_table.drop(migrate_engine, checkfirst=True)