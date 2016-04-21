#! /bin/bash

# Set up env
export PSPKG_ROOT=/reg/common/package
export PSPKG_RELEASE=controls-0.0.8
source $PSPKG_ROOT/etc/set_env.sh
source /reg/g/pcds/setup/pyca27.sh

# Check if this is amo or sxr
if [[ "${2:0:3}" == "SXR" ]] || [[ "${2:0:3}" == "AMO" ]]; then
    sxd=true
else
    sxd=false
fi

# Check if this is xpp or xcs
if [[ "${2:0:3}" == "XPP" ]] || [[ "${2:0:3}" == "XCS" ]]; then
    hxr=true
else
    hxr=false
fi

# Check for hutch-specific options
dir=`dirname $(readlink -f "$0")`
if [[ "$1" == "apply" ]] && [ "$sxd" = true ] ; then
    python $dir/pmgrUtils.py $1 $2 -v -z --hutch=sxd
elif [ "$hxr" = true ] ; then
    python $dir/pmgrUtils.py $1 $2
else
    python $dir/pmgrUtils.py $1 $2 -v -z
fi
