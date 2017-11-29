#!/usr/bin/env python
"""util.py

Copyright Tobias C Wood 2017

Utility functions for nanslice module"""
from collections import namedtuple
import argparse
import numpy as np
import scipy.ndimage.interpolation as ndinterp
from . import image
from .slice import axis_map, axis_indices

def sample_point(img, point, order=1):
    scale = np.mat(img.get_affine()[0:3, 0:3]).I
    offset = np.dot(-scale, img.get_affine()[0:3, 3]).T
    s_point = np.dot(scale, point).T + offset[:]
    return ndinterp.map_coordinates(img.get_data().squeeze(), s_point, order=order)

def center_of_mass(img):
    idx0 = np.argmax(np.sum(img.get_data(), axis=(1,2)))
    idx1 = np.argmax(np.sum(img.get_data(), axis=(0,2)))
    idx2 = np.argmax(np.sum(img.get_data(), axis=(0,1)))
    phys = np.dot(img.affine, np.array([idx0, idx1, idx2,1]).T)
    return phys

Options = namedtuple("Options",
                     "interp_order color_map color_lims color_scale color_mask_thresh alpha_lims")

def overlay_slice(sl, options, window,
                  img_base, img_mask,
                  img_color, img_color_mask,
                  img_alpha):
    """Creates a slice through a base image, with a color overlay and specified alpha"""
    sl_base = image.colorize(sl.sample(img_base, order=options.interp_order),
                             'gray', window)
    if img_color:
        sl_color = sl.sample(img_color, order=options.interp_order) * options.color_scale
        if img_color_mask:
            sl_color_mask = sl.sample(img_color_mask, order=options.interp_order)
            if options.color_mask_thresh:
                sl_color_mask = sl_color_mask > options.color_mask_thresh
        elif options.color_mask_thresh:
            sl_color_mask = sl_color > options.color_mask_thresh
        else:
            sl_color_mask = np.ones_like(sl_color)
        sl_color = image.colorize(sl_color, options.color_map, options.color_lims)
        sl_color = image.mask(sl_color, sl_color_mask)
        if img_alpha:
            sl_alpha = sl.sample(img_alpha, order=options.interp_order)
            sl_scaled_alpha = image.scale_clip(sl_alpha, options.alpha_lims)
            sl_blend = image.blend(sl_base, sl_color, sl_scaled_alpha)
        else:
            sl_blend = image.blend(sl_base, sl_color, sl_color_mask)
    else:
        sl_blend = sl_base
    if img_mask:
        sl_final = image.mask(sl_blend,
                              sl.sample(img_mask, options.interp_order))
    else:
        sl_final = sl_blend
    return sl_final

def draw_slice(axis, sl, opts, window, img, mask,
               color_img=None, color_mask=None, alpha_img=None,
               contour_img=None, contour_levels=(0.95,), contour_colors='w'):
    sliced = overlay_slice(sl, opts, window, img, mask, color_img, color_mask, alpha_img)
    axis.imshow(sliced, origin='lower', extent=sl.extent, interpolation='none')
    axis.axis('off')
    if contour_img:
        sliced_contour = sl.sample(contour_img, order=1)
        if (sliced_contour < contour_levels[0]).any() and (sliced_contour > contour_levels[0]).any():
            axis.contour(sliced_contour, levels=contour_levels,
                        origin='lower', extent=sl.extent,
                        colors=contour_colors, linewidths=1)

def crosshairs(axis, point, direction, orient, color='g'):
    ind1, ind2 = axis_indices(axis_map[direction], orient)
    vline = axis.axvline(x=point[ind1], color=color)
    hline = axis.axhline(y=point[ind2], color=color)
    return (vline, hline)

def colorbar(axes, cm_name, clims, clabel,
             black_backg=True, show_ticks=True, tick_fmt='{:.0f}', orient='h'):
    """Plots a 2D colorbar (color/alpha)"""
    steps = 32
    if orient == 'h':
        ext = (clims[0], clims[1], 0, 1)
        cdata = np.tile(np.linspace(clims[0], clims[1], steps)[np.newaxis, :], [steps, 1])
    else:
        ext = (0, 1, clims[0], clims[1])
        cdata = np.tile(np.linspace(clims[0], clims[1], steps)[:, np.newaxis], [1, steps])
    color = image.colorize(cdata, cm_name, clims)
    axes.imshow(color, origin='lower', interpolation='hanning', extent=ext, aspect='auto')
    if black_backg:
        forecolor = 'w'
    else:
        forecolor = 'k'
    if show_ticks:
        ticks = (clims[0], np.sum(clims)/2, clims[1])
        labels = (tick_fmt.format(clims[0]), clabel, tick_fmt.format(clims[1]))
        if orient == 'h':
            axes.set_xticks(ticks)
            axes.set_xticklabels(labels, color=forecolor)
            axes.set_yticks(())
        else:
            axes.set_yticks(ticks)
            axes.set_yticklabels(labels, color=forecolor, rotation='vertical', va='center')
            axes.set_xticks(())
    else:
        if orient == 'h':
            axes.set_xticks((np.sum(clims)/2,))
            axes.set_xticklabels((clabel,), color=forecolor)
        else:
            axes.set_yticks((np.sum(clims)/2,))
            axes.set_yticklabels((clabel,), color=forecolor)
    axes.tick_params(axis='both', which='both', length=0)
    axes.spines['top'].set_color(forecolor)
    axes.spines['bottom'].set_color(forecolor)
    axes.spines['left'].set_color(forecolor)
    axes.spines['right'].set_color(forecolor)
    axes.yaxis.label.set_color(forecolor)
    axes.xaxis.label.set_color(forecolor)
    axes.axis('on')

def alphabar(axes, cm_name, clims, clabel,
             alims, alabel, alines=None, alines_colors=('k',), alines_styles=('solid',),
             cprecision=1, aprecision=0,
             black_backg=True, orient='h'):
    """Plots a 2D colorbar (color/alpha)"""
    steps = 32
    if orient == 'h':
        ext = (alims[0], alims[1], clims[0], clims[1])
        cdata = np.tile(np.linspace(clims[0], clims[1], steps)[np.newaxis, :], [steps, 1])
        alpha = np.tile(np.linspace(0, 1, steps)[:, np.newaxis], [1, steps])
    else:
        ext = (alims[0], alims[1], clims[0], clims[1])
        cdata = np.tile(np.linspace(clims[0], clims[1], steps)[:, np.newaxis], [1, steps])
        alpha = np.tile(np.linspace(0, 1, steps)[np.newaxis, :], [steps, 1])
    color = image.colorize(cdata, cm_name, clims)
    
    backg = np.ones((steps, steps, 3))
    acmap = image.blend(backg, color, alpha)
    axes.imshow(acmap, origin='lower', interpolation='hanning', extent=ext, aspect='auto')

    cticks = (clims[0], np.sum(clims)/2, clims[1])
    cfmt = '{:.'+str(cprecision)+'f}'
    clabels = (cfmt.format(clims[0]), clabel, cfmt.format(clims[1]))
    aticks = (alims[0], np.sum(alims)/2, alims[1])
    afmt = '{:.'+str(aprecision)+'f}'
    alabels = (afmt.format(alims[0]), alabel, afmt.format(alims[1]))

    if orient == 'h':
        axes.set_xticks(cticks)
        axes.set_xticklabels(clabels)
        axes.set_yticks(aticks)
        axes.set_yticklabels(alabels, rotation='vertical')
    else:
        axes.set_xticks(aticks)
        axes.set_xticklabels(alabels)
        axes.set_yticks(cticks)
        axes.set_yticklabels(clabels, rotation='vertical', va='center')
    
    if alines:
        for ay, ac, astyle in zip(alines, alines_colors, alines_styles):
            if orient == 'h':
                axes.axhline(y=ay, linewidth=1.5, linestyle=astyle, color=ac)
            else:
                axes.axvline(y=ay, linewidth=1.5, linestyle=astyle, color=ac)
    
    if black_backg:
        axes.spines['bottom'].set_color('w')
        axes.spines['top'].set_color('w')
        axes.spines['right'].set_color('w')
        axes.spines['left'].set_color('w')
        axes.tick_params(axis='x', colors='w')
        axes.tick_params(axis='y', colors='w')
        axes.yaxis.label.set_color('w')
        axes.xaxis.label.set_color('w')
    else:
        axes.spines['bottom'].set_color('k')
        axes.spines['top'].set_color('k')
        axes.spines['right'].set_color('k')
        axes.spines['left'].set_color('k')
        axes.tick_params(axis='x', colors='k')
        axes.tick_params(axis='y', colors='k')
        axes.yaxis.label.set_color('k')
        axes.xaxis.label.set_color('k')
        axes.axis('on')

def common_options():
    """Defines a set of common arguments that are shared between viewer and slicer"""
    parser = argparse.ArgumentParser(description='Dual-coding viewer.')
    parser.add_argument('base_image', help='Base (structural image)', type=str)
    parser.add_argument('--mask', type=str,
                        help='Mask image')

    parser.add_argument('--color', type=str,
                        help='Add color overlay')
    parser.add_argument('--color_lims', type=float, noptions=2, default=(-1, 1),
                        help='Colormap window, default=-1 1')
    parser.add_argument('--color_mask', type=str,
                        help='Mask color image')
    parser.add_argument('--color_mask_thresh', type=float,
                        help='Color mask threshold')
    parser.add_argument('--color_scale', type=float, default=1,
                        help='Multiply color image by value, default=1')
    parser.add_argument('--color_map', type=str, default='RdYlBu_r',
                        help='Colormap to use from Matplotlib, default = RdYlBu_r')
    parser.add_argument('--color_label', type=str, default='% Change',
                        help='Label for color axis')

    parser.add_argument('--alpha', type=str,
                        help='Image for transparency-coding of overlay')
    parser.add_argument('--alpha_lims', type=float, noptions=2, default=(0.5, 1.0),
                        help='Alpha/transparency window, default=0.5 1.0')
    parser.add_argument('--alpha_label', type=str, default='1-p',
                        help='Label for alpha/transparency axis')
    
    parser.add_argument('--contour_img', type=str,
                        help='Image to define contour (if none, use alpha image)')
    parser.add_argument('--contour', type=float, action='append',
                        help='Add an alpha image contour (can be multiple)')
    parser.add_argument('--contour_color', type=str, action='append',
                        help='Choose contour colour')
    parser.add_argument('--contour_style', type=str, action='append',
                        help='Choose contour line-style')

    parser.add_argument('--window', type=float, noptions=2, default=(1, 99),
                        help='Specify base image window (in percentiles)')
    parser.add_argument('--samples', type=int, default=128,
                        help='Number of samples for slicing, default=128')
    parser.add_argument('--interp', type=str, default='hanning',
                        help='Display interpolation mode, default=hanning')
    parser.add_argument('--interp_order', type=int, default=1,
                        help='Data interpolation order, default=1')
    parser.add_argument('--orient', type=str, default='clin',
                        help='Clinical (clin) or Pre-clinical (preclin) orientation')
    return parser