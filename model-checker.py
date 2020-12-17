#!/usr/bin/env python3

# This file is part of the Simple LTL model-checker project
# see https://github.com/fredher/simple-ltl-model-checker

import argparse
import spot
import sys
from buddy import bdd_ithvar, bddtrue
import pygraphviz as pgv

""" 
The input file should follow the graphviz DOT file format. Nodes may have
attributes:
- 'initial' (with any non-empty value) if the node is initial. The model should
  specify exactly one initial node
- 'labels' (non-empty comma-separated list of strings) defines the list of
  atomic propositions that label the node
"""

def extract_node_str_labels(n):
    """ Extract the set of string labels from node n (attribute labels) """
    labels = set()
    for label in n.attr['labels'].split(','):
        if label != '':
            labels.add(label)
    return labels

def extract_nodes_str_labels(G):
    """ Extract the set of string labels from all nodes in graph G (attribute
    labels on nodes in G) """
    labels = set()
    for n in G.nodes():
        labels = labels.union(extract_node_str_labels(n))
    return labels

def extract_initial_node(G):
    """ Extract initial node from graph G (attribute initial on nodes in G) """
    initial_node_name = ''
    for n in G.nodes():
        if n.attr['initial'] != '':
            if initial_node_name != '':
                raise 'Multiple initial states are not allowed'
            initial_node_name = n
    if initial_node_name == '':
        raise 'One initial state must be defined'
    return initial_node_name

def node_AP_formula_bdd(n, AP):
    """ Build formula of atomic formula for node n over set of atomic
    propositions AP """
    n_labels = extract_node_str_labels(n)
    f = bddtrue
    for l in AP:
        if l in n_labels:
            f = f & AP[l]
        else:
            f = f & -AP[l]
    return f

def dot_model_to_kripke(file, bdddict):
    """ Create a Kripke structure from a DOT file. Nodes may have attributes:
    'initial' (with any non-empty value) if the node is initial, and 'labels'
    (comma-separated list of strings) to define atomic propositions labeling the
    node """
    k = spot.make_kripke_graph(bdddict)
    G = pgv.AGraph(file)
    # Extract node labels in G
    G_labels = extract_nodes_str_labels(G)
    # Declare atomic propositions
    AP = {}
    for l in G_labels:
        AP[l] = bdd_ithvar(k.register_ap(l))
    # Declare nodes
    k_nodes = {}
    node_names = []
    for n in G.nodes():
        f = node_AP_formula_bdd(n, AP)
        k_nodes[n] = k.new_state(f)
        node_names = node_names + [n]
    k.set_state_names(node_names)
    # Declare initial node
    initial_node = extract_initial_node(G)
    k.set_init_state(k_nodes[initial_node])
    # Declare transitions
    for (src, tgt) in G.edges():
        k.new_edge(k_nodes[src], k_nodes[tgt])
    return k

def build_automaton(formula, bdddict):
    """ Build a Büchi automaton that accepts all words satisfying formula, using
dictionary bdddict """
    af = spot.translate(formula, dict=bdddict)
    return af

def model_check(k, formula, bdddict):
    """ model-check Kripke structure k w.r.t. LTL formula using BDD dictionary
   bdddict """
    # Create the automaton for the negation of the formula
    neg_formula = "!(" + formula + ")"
    a_neg_formula = build_automaton(neg_formula, d)
    # Compute the product
    product = spot.otf_product(k, a_neg_formula)
    # Check emptiness of the product
    run = product.accepting_run()
    return (a_neg_formula, product, run)

def write_to_file(filename, str):
    """ Write string str to file filename """
    try:
        f = open(filename, "w")
        f.write(str)
        f.close()
    except:
        print("ERROR, writing to file", filename, "failed")
        sys.exit()

# Command line parser
parser = argparse.ArgumentParser()
parser.add_argument("model", type=str, nargs=1, help=""" model file name """)
parser.add_argument("formula", type=str, nargs=1, help=""" LTL formula to check
""")
parser.add_argument("--output", type=str, nargs=1, help=""" output kripke
structure, automaton and product using OUTPUT as a file name prefix """)
args = parser.parse_args()

filename = args.model[0]
formula = args.formula[0]
if args.output:
    outfilename = args.output[0]

print("Checking formula", formula, "on file", filename, end='...')
d = spot.make_bdd_dict()
k = dot_model_to_kripke(filename, d)
(a, p, run) = model_check(k, formula, d)
if run:
    print("FAILED\nCounter-example:\n", run)
else:
    print("SUCCESS")

if (args.output):
    k_filename=outfilename+"-kprike.dot"
    print("Writing the Kripke structure in file", k_filename)
    write_to_file(k_filename, k.to_str('dot'))

    a_filename=outfilename+"-automaton.dot"
    print("Writing the Büchi automaton for !("+formula+") in file", a_filename)
    write_to_file(a_filename, a.to_str('dot'))

    p_filename=outfilename+"-product.dot"
    print("Writing the product automaton in file", p_filename)
    write_to_file(p_filename, p.to_str('dot'))
