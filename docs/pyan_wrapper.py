"""
Wrapper around pyan to create call graph and dependcy dotfiles.
"""
import pyan
import sys

outfile = sys.argv[1]
module_files = sys.argv[2:]

callgraph = pyan.create_callgraph(module_files, format='dot', draw_defines=False, nested_groups=False, grouped=False)

with open(f"flow_{outfile}", 'w') as f:
    f.write(callgraph)

callgraph = pyan.create_callgraph(module_files, format='dot', draw_defines=False, nested_groups=True, grouped=True)

with open(f"grouped_{outfile}", 'w') as f:
    f.write(callgraph)
