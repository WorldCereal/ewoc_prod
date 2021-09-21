=========
ewoc-prod
=========

ewoc-prod package is in charge to run production from end to end


Description
===========

Aux data: AEZ with tiles id by AEZ region

EWoc k8s cluster mode 
----------------------

Prerequesites:

* a ewoc k8s cluster
* a ewoc database hosted on a node of the k8s cluster 

This code is plan to run by default on the bastion of the k8s creodias cluster and from the master node for aws k8s cluster 

EWoc local mode 
----------------------
Prerequesites:

* a ewoc database provided by a docker image

.. code-block:: sh

    docker run --name ewoc_db --network host -p 5432:5432 -e POSTGRES_PASSWORD=password -d -v /path/to/postgres_database_dir/:/var/lib/postgresql/data postgres
    psql -h localhost -p 5432 -U postgres postgres -f world_cereal_db_init.sql

WARNING: the local mode must limited to process one tile on short period for test purpose! 

.. _pyscaffold-notes:

Note
====

This project has been set up using PyScaffold 4.0.2. For details and usage
information on PyScaffold see https://pyscaffold.org/.
