# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Importing SimaPro CSV files
#
# This notebooks demonstrates how to use the `bw2io.SimaProBlocCSVImporter` to import LCI created in SimaPro into brightway. 
# It uses brightway 2.5.
#
# The notebook is split in 2 sections:
#
# 1. Importing an LCI that only has references (i.e. _Exchanges_) to either Biosphere flows or to itself.
# 2. Importing an LCI that includes references to another "`library`" (as SimaPro calls them) like ecoinvent.

# %%
from pathlib import Path

import bw2data as bd
import bw2io as bi
import bw_simapro_csv # only import it here to printe the version of the module. We will use it through bw2io
from pprint import pprint

# %%
print(f"Using bw2data version: {bd.__version__}")
print(f"Using bw2io version: {bi.__version__}")
print(f"Using bw_simapro_csv version: {bw_simapro_csv.__version__}")

# %% [markdown]
# ## The imported inventories
# The LCIs created in simapro mimic the LCI of a bike as depicted in [from the ground up notebooks](https://github.com/brightway-lca/from-the-ground-up/).
#
# ### Bike
# The first inventory exported from SimaPro is the [bike_example_no_ei.CSV](bike_example_no_ei.CSV) file. It only includes the following products:
#
# + Bike
# + Carbon fibre
# + Natural gas
#
# and their corresponding "Processes":
#
# + Bike production
# + CF production
# + NG Production
#
# Below is a graphical depiction of the supply chain:
#
# ![supply-chain-simple.png](supply-chain-simple.png)
#
# ### Bike 2
#
# This inventory, additionally includes as input electricity from Norway as an input (i.e. "_exchange_") for the `CF production` process.
#
#

# %% [markdown]
# ## Importing LCIs with only self references

# %%
bd.projects

# %%
bd.projects.set_current("ecoinvent311")
# This project already includes ecoinvent 3.11 cutoff, which is necessary for section 2
bd.databases

# %% [markdown]
# ### Use the _real_ SimaPro importer that does all the magic
#
# Although the `bw_simapro_csv` [package](https://github.com/brightway-lca/bw_simapro_csv) has the main functionalities that parse and interpret the SimaPro CSV, it is not a "regular" brightway importer. That is, it does not in clude `strategies` to be applied (for example, to normalize units, or to parse the names of ecoinvent extracting the location from them.
#
# The right way to proceed is to use the `bi.SimaProBlockCSVImporter`, apply the strategies and then fiddle the data if there are unlinked exchanges.

# %%
spi = bi.SimaProBlockCSVImporter(Path("bike_example_no_ei.CSV"))

# %%
# Do some well known changes to data, based on simapro standards by applying the strategies.
spi.apply_strategies()

# %%
# Verify the status of the importer
# We must verify here that we have:
# 6 graph nodes (3 for the products, 3 for the processes) and 
# 6 edges (see the supply chain scheme above)
spi.statistics()

# %% [markdown]
# At this point, the `spi` importer shows that we have unlinked edges, because we haven't matched yet the data neither to the own database we are trying to import, nor to the `ecoinvent-3.11-biosphere` (nor `ecoinvent-3.11-cutoff`, but this is for section 3)

# %% [markdown]
# ### Matching

# %% [markdown]
# #### Match the database we are importing against itself

# %%
spi.match_database()

# %%
# We verify again the status of the importer
spi.statistics()

# %% [markdown]
# At this point, normally, all self references to the database we are importing should be resolved, and we should only have one unlinked edge related to the biosphere.

# %% [markdown]
# #### Match against the biosphere

# %%
spi.match_database("ecoinvent-3.11-biosphere")

# %%
spi.statistics()

# %% [markdown]
# At this point, we know there is one biosphere flow that was not automagically matched before.
# We can print to see which flow it is

# %%
# print the unlinked flows
# We know it's CO2
for u in spi.unlinked:
    print(u)

# %%
# find CO2 from the biosphere
for flow in bd.Database("ecoinvent-3.11-biosphere"):
    if "Carbon dioxide, fossil" in flow["name"] and flow["categories"] == ("air",):
        print(flow.as_dict())
        co2_flow = flow

# %%
# add as input the CO2 to the exchanges in the imported data
for p in spi.data:
    for e in p.get("exchanges", []):
        if e["type"] == "biosphere":
            e["input"] = co2_flow.key

# %%
spi.statistics()

# %% [markdown]
# Now that the importer reports no unlinked edges, we can proceed to write the database and do some first tests.

# %%
spi.write_database()

# %%
for p in bd.Database("bike_example"):
    if p["type"] == "product" and p['name'] == 'Bike':
        print(p)        
        bike_p = p

# %%
import bw2calc as bc

# %%
ef_method_cc = [m for m in bd.methods if m[1] == "EF v3.1" and m[2] == "climate change"]
ef_method_cc

# %%
functional_unit, data_objs, _ = bd.prepare_lca_inputs(
    {bike_p: 1}, method=ef_method_cc[0],remapping=False
)

# %%
lca = bc.LCA(demand=functional_unit, data_objs=data_objs)
lca.lci()
lca.lcia()
lca.score

# %% [markdown]
# ## Importing LCIs with external references

# %%
ext_spi = bi.SimaProBlockCSVImporter(Path('bike_example_with_ei.CSV'))

# %%
#ext_spi.use_ecoinvent_strategies()
ext_spi.apply_strategies()

# %%
ext_spi.statistics()

# %% [markdown]
# ### Match the databases

# %%
# First, against itself
ext_spi.match_database()

# %%
ext_spi.statistics()

# %%
# add as input the CO2 to the exchanges in the imported data
for p in ext_spi.data:
    for e in p.get("exchanges", []):
        if e["type"] == "biosphere":
            e["input"] = co2_flow.key
            e["categories"] = co2_flow['categories']

# %%
ext_spi.match_database('ecoinvent-3.11-cutoff', fields=["name", "unit", "location", "reference product"])
ext_spi.statistics()

# %%
ext_spi.use_ecoinvent_strategies()
ext_spi.apply_strategies()

# %%
ext_spi.statistics()

# %% [markdown]
# The biosphere flow seems to be well replaced, but now the only technosphere flow is missing (presumable the one from ecoinvent).
# Let's look at it in detail.

# %%
for u in ext_spi.unlinked:
    pprint(u)

# %%
ext_spi.match_database('ecoinvent-3.11-cutoff')

# %%
ext_spi.statistics()

# %%
resulting_excel = ext_spi.write_excel()

# %%
import shutil
import os

# %%
# Destination is the current working directory
destination = Path.cwd() / resulting_excel.name

# Copy the file
shutil.copy(resulting_excel, destination)

print(f"Copied {resulting_excel} to {destination}")

# %%
# Find the electricity dataset we want
ei_db = bd.Database('ecoinvent-3.11-cutoff')

# %%
results = ei_db.search('market for electricity, medium voltage', limit=10000)
for r in results:
    if r['location'] == 'NO' and 'market for electricity, medium voltage' == r['name']:
        print(r)

# %%
for d in ext_spi.data:
    if 'exchanges' in d:
        for exc in d['exchanges']:            
            if exc['name'] == 'Electricity, medium voltage {NO}| market for electricity, medium voltage | Cut-off, U':
                print(exc)
                # add the input as it should
                exc['name'] = r['name']
                exc['input'] = r.key
        

# %%
spi.statistics()

# %%
spi.write_database()
