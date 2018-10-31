#
# Copyright (c) 2016 SUSE Linux GmbH
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 3 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, contact SUSE LLC.
#
# To contact SUSE about this file by physical or electronic mail,
# you may find current contact information at www.suse.com

"""
Transform the RSTXML file into DocBook
"""

from lxml import etree
import logging
import os

from .util import quoteparams
from .struct import addchapter, addlegalnotice
from ..cleanup import cleanupxml
from ..core import XSLTRST2DB, XSLTRESOLVE, XSLTSPLIT, XSLTMOVEBLOCKS


log = logging.getLogger(__name__)


def logging_xslt(resultxslt, logger=log):
    """Log result from XSLT transformation

    :param resultxslt:
    :type resultxslt: :class:`etree._XSLTResultTree`
    :param logger:
    :type logger: :class:`logging.Logger`
    """
    for entry in resultxslt.error_log:
        level, msg = entry.message.split(':', maxsplit=1)
        msg = msg.strip()
        log.log(getattr(logging, level, 'INFO'), "%s", msg)


def step_blockelements_transform(tree, args):
    """Moves block elements inside <paragraphs> outside
       of <paragraphs>

    :param tree: tree of class :class:`lxml.etree._ElementTree`
    :param args: argument result from :class:`argparse`
    :return: XML tree
    :rtype: :class:`lxml.etree._ElementTree`
    """
    xslt = etree.XSLT(etree.parse(XSLTMOVEBLOCKS))
    log.debug("Starting to cleanup paragraphs")
    xml = xslt(tree)
    return xml


def step_resolve_transform(tree, args):
    """Resolve any outgoing references in the RST XML document

    :param tree: tree of class :class:`lxml.etree._ElementTree`
    :param args: argument result from :class:`argparse`
    :return: XML tree
    :rtype: :class:`lxml.etree._ElementTree`
    """
    xslt = etree.XSLT(etree.parse(XSLTRESOLVE))
    log.debug("Starting to resolve multiple RST XML "
              "into a single RST XML file")
    xml = xslt(tree)
    # logging_xslt(xslt)
    # log.debug("Resolved all external references")
    # xml.write(
    #    '/tmp/trees/resolve-tree.xml',
    #    encoding='utf-8',
    #    pretty_print=True,
    #    )
    # log.debug("Wrote resolved tree to '/tmp/tree.xml'")
    log.debug("Created single RST XML file")
    return xml


def step_rst2db_transform(tree, args):
    """Transform RST XML into DocBook 5

    :param tree: tree of class :class:`lxml.etree._ElementTree`
    :param args: argument result from :class:`argparse`
    :return: XML tree
    :rtype: :class:`lxml.etree._ElementTree`
    """
    xslt = etree.XSLT(etree.parse(XSLTRST2DB))
    xml = xslt(tree, **dict(args.params))
    # xml.write(
    #    '/tmp/trees/db5-tree.xml',
    #    encoding='utf-8',
    #    pretty_print=True,
    #    )
    # log.debug("Wrote result tree to '/tmp/result-tree.xml'")
    log.debug("Transformed RST XML into DocBook 5")
    logging_xslt(xslt)
    if args.legalnotice is not None:
        addlegalnotice(xml, args.legalnotice)
    if args.conventions is not None:
        addchapter(xml, args.conventions)
    return xml


def transform(doc, args):
    """Transformation step

    :param doc: tree of class :class:`lxml.etree._ElementTree`
    :param args: argument result from :class:`argparse`
    :return: XML tree
    :rtype: :class:`lxml.etree._ElementTree`
    """
    xml = step_resolve_transform(doc, args)
    xml = step_blockelements_transform(xml, args)
    xml = step_rst2db_transform(xml, args)
    cleanupxml(xml)

    if not args.nsplit:
        xml_split_tree = etree.parse(XSLTSPLIT)
        xml_split_trans = etree.XSLT(xml_split_tree)
        xml_split_trans(xml, **dict(args.params))
    #   xml.write(
    #        '/tmp/trees/split-tree.xml',
    #        encoding='utf-8',
    #        pretty_print=True,
    #        )
        logging_xslt(xml_split_trans)
        return None

    return xml


def process(args):
    """Process arguments from CLI parser

    :param args: result from `argparse` parser
    :return: True or False
    :rtype: bool
    """
    doc = etree.parse(args.indexfile)

    xmldict = dict(
        encoding='unicode',
        pretty_print=True,
        )

    if args.output is None:
        if not args.nsplit:
            os.makedirs('out/', exist_ok=True)
    else:
        args.outputdir = os.path.dirname(args.output)
        args.outputdir = args.outputdir if args.outputdir else "."
        os.makedirs(args.outputdir, exist_ok=True)
        if not args.nsplit:
            args.params.append(('basedir',  "%s/" % args.outputdir))
    args.params = quoteparams(args)
    xml = transform(doc, args)

    if args.output is not None and xml is not None:
        outstring = etree.tostring(xml, **xmldict)
        with open(args.output, 'w') as f:
            log.info("Writing results to %r...", args.output)
            f.write(outstring)
    elif xml is not None:
        outstring = etree.tostring(xml, **xmldict)
        print(outstring)

    return 0
