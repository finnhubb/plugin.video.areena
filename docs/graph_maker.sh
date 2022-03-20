#!/bin/bash

# Uses pyan to create three following graphs for the yle areena kodi addon:
# Grouped function call graph
# Ungrouped (flow) function call graph
# Module dependency graph

shopt -s nullglob

if test "$BASH" = "" || "$BASH" -uc "a=();true \"\${a[@]}\"" 2>/dev/null; then
    # Bash 4.4, Zsh
    set -euo pipefail
else
    # Bash 4.3 and older chokes on empty arrays with set -u.
    set -eo pipefail
fi


cleanup() {
    rm -rf "$tmpdir"
}

trap cleanup EXIT

tmpdir=$(mktemp -d)
touch "${tmpdir}/moddeps"
ADDONPATH="../plugin.video.areena"
LIBPATH="${ADDONPATH}/resources/lib"
OUTDIR="./"

# Create module dependency list.
for filepath in "$LIBPATH"/*.py; do
    file="${filepath##*/}"
    # Flatten the relative imports used by kodi
   sed -E -e 's_from resources\.lib\.([^ ]*) (.*)_import \1_g' -e 's_from resources\.lib __g' "$filepath" > "${tmpdir}/${file#*/}"

    # catches imports of 'from resource.lib.module import xyz', 'from resource.lib import module', 'import xbmc*'
    sed -En '/import/ s_from resources\.lib\.([^ ]*) (.*)_\1_gp; s_from resources\.lib import __gp; s_import (xbmc.*)_\1_gp' \
           "$filepath" >> "${tmpdir}/moddeps"
done

# Create list of external depdendencies
readarray -t extmodules < <(pipreqs "$ADDONPATH" --print 2>/dev/null | cut -d '=' -f 1 | grep -v 'resources')

# Create dummy modules for any imports
readarray -t importedmodules < <(cat "${tmpdir}/moddeps")
readarray -t importedmodules < <(printf '%s\n' "${extmodules[@]}" "${importedmodules[@]}"| sort -u)
for module in "${importedmodules[@]}"; do
    if [ ! -f "${tmpdir}/${module}.py" ]; then
        extmodules+=("$module")
        touch "${tmpdir}/${module}.py"
    fi
done

readarray -t extmodules < <(printf '%s\n' "${extmodules[@]}" | sort -u)


# Create list of all modules
declare -a allmodules
for file in "$tmpdir"/*.py; do
    filename="${file##*/}"
    allmodules+=("${filename%.*}")
done

# Generate the dotfiles containing graph nodes and edges with pyan.
dotfile="graph.dot"
python3 pyan_wrapper.py "$dotfile" "${tmpdir}"/*.py

# Generate grouped function callgraph.
dotfile="grouped_graph.dot"
# Remove the modules as nodes in the graph (since the nodes are grouped by module)
readarray dotgraph < "$dotfile"

for module_name in "${allmodules[@]}"; do
    readarray dotgraph < <(printf '%s' "${dotgraph[*]}" | grep -v "^[ ]*${module_name}[ -]")
    continue
done

printf '%s' "${dotgraph[*]}" | dot -Tsvg > "${OUTDIR}/grouped_functioncall_graph.svg"

# Generate flowing function callgraph.
dotfile='flow_graph.dot'
readarray dotgraph < <(grep -v 'log' "$dotfile")

# Add the colors the the modules matching the color for their methods group.
for module_name in "${allmodules[@]}"; do
    # Extract the color used to fill methods belonging to this module.
    module_color=$(printf '%s' "${dotgraph[*]}" | grep "${module_name}__" | grep -Po fillcolor='[^,]*' | head -n 1) || true
    # If no color was extracted, use the default.
    module_color="${module_color:-fillcolor=\"#ff000000\"}"
    # Replace the uncolored module with its module color.
    readarray dotgraph < <(printf '%s' "${dotgraph[*]}" | sed -E "/label=\"${module_name}\"/ s_fillcolor=[^,]*_${module_color}_g")
done

# Extract modules to create module dependency graph.
printf '%s' "${dotgraph[*]}" | grep -v '__' > 'modules_graph.dot'
dot -Tsvg 'modules_graph.dot' > "${OUTDIR}/module_dependency_graph.svg"

# Remove the external modules from the function call graph
for module_name in "${extmodules[@]}"; do
    readarray dotgraph < <(printf '%s\n' "${dotgraph[@]}" | sed -E "/${module_name}/d")
done

# Remove the modules edges to create function callgraph.
printf '%s' "${dotgraph[*]}" | grep -v '^[ ]*[a-z]* -> [a-z]* ' | dot -Tsvg > "${OUTDIR}/flow_functioncall_graph.svg"

# cleanup
exit 0
