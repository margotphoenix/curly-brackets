from functools import wraps

from pandas import Series, DataFrame


def slow_apply(groupby, func, *args, **kwargs):
    """ Applies a function to a pandas GroupBy object. This is useful when the
        applied function takes a long time to run. The traditional GroupBy.apply
        has the function run twice on the first group, where the first run determines
        whether pandas will use a fast or slow method to apply the function to all the
        groups. This function skips that extra call and just runs the function once
        on each group via the slow path.

    Parameters
    ----------
    groupby : pandas.GroupBy
        pandas.GroupBy object on which to apply the function
    func : function
        callable function to apply to each group in the GroupBy
    *args, **kwargs : tuple, dict
        optional positional and keyword arguments passed to func

    Returns
    -------
    pandas DataFrame or Series
    """
    grouper = groupby.grouper

    mutated = grouper.mutated
    splitter = grouper._get_splitter(groupby._selected_obj, groupby.axis)
    group_keys = grouper._get_group_keys()

    result_values = []
    for key, group in zip(group_keys, splitter):
        object.__setattr__(group, 'name', key)

        if isinstance(group, Series):
            group_axes = [group.index]
        else:
            group_axes = group.axes

        # print("Applying function to group '{}'".format(key))
        res = func(group, *args, **kwargs)

        if (not isinstance(res, (Series, DataFrame)) or
                not res.index.equals(group_axes[0]) or
                (isinstance(res, Series) and len(group_axes) > 1)):
            mutated = True
        result_values.append(res)

    return groupby._wrap_applied_output(groupby._selected_obj, group_keys, result_values,
                                        not_indexed_same=mutated or groupby.mutated)
