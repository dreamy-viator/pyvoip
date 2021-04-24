#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
#from audio_out import AudioOutput

"""Tests for a high-level Decoder object"""

import unittest
import opuslib

#__author__ = 'Никита Кузнецов <self@svartalf.info>'
#__copyright__ = 'Copyright (c) 2012, SvartalF'
#__license__ = 'BSD 3-Clause License'


class EncoderTest(unittest.TestCase):
    def test_create(self):
        try:
            #opuslib.Encoder(1000, 3, opuslib.APPLICATION_AUDIO)
            opuslib.Encoder(1000, 3, opuslib.APPLICATION_VOIP)
        except opuslib.OpusError as ex:
            self.assertEqual(ex.code, opuslib.BAD_ARG)
        #opuslib.Encoder(48000, 2, opuslib.APPLICATION_AUDIO)
        opuslib.Encoder(48000, 2, opuslib.APPLICATION_VOIP)

    @classmethod
    def test_reset_state(cls):
        #encoder = opuslib.Encoder(48000, 2, opuslib.APPLICATION_AUDIO)
        encoder = opuslib.Encoder(48000, 2, opuslib.APPLICATION_VOIP)
        encoder.reset_state()
