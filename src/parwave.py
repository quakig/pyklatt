# -*- coding: utf-8 -*-
"""
Klatt CPSC 599 module: src.parwave

Purpose
=======
 Provides functionality for generating waveform samples from format parameter
 data.
 
Legal
=====
 All code, unless otherwise indicated, is original, and subject to the
 terms of the GPLv2, which is provided in COPYING.
 
 Core algorithms derived from the C implementation of the Klatt synthesizer by
 Jon Iles and Nick Ing-Simmons, with full attribution provided in
 ACKNOWLEDGEMENTS.
 
 (C) Neil Tallim, Sydni Bennie, 2009
"""
import math
import random
			
class Synthesizer(object):
	_noise = 0.0
	
	def __init__(self):
		pass
		
	def _initSynthesizers(self, frequencies, bandwidths):
		pi_neg_div = math.pi * -0.0001
		pi_2_div = 2.0 * math.pi * 0.0001
		pi_neg_2_div = -pi_2_div
		
		b = (bgp, bgz, bgs, bnp, bnz, b1, b2, b3, b4, b5, b6) = [n * m for (n, m) in zip([math.cos(pi_2_div * f) for f in frequencies], [2 * math.e ** (pi_neg_div * bw) for bw in bandwidths])]
		c = (cgp, cgz, cgs, cnp, cnz, c1, c2, c3, c4, c5, c6) = [-math.e ** (pi_neg_2_div * bw) for bw in bandwidths]
		a = (agp, agz, ags, anp, anz, a1, a2, a3, a4, a5, a6) = [1 - b_v - c_v for (b_v, c_v) in zip(b, c)]
		
		return (
		 (
		  _Resonator(a1, b1, c1),
		  _Resonator(a2, b2, c2),
		  _Resonator(a3, b3, c3),
		  _Resonator(a4, b4, c4),
		  _Resonator(a5, b5, c5),
		  _Resonator(a6, b6, c6)
		 ),
		 (
		  _Resonator(a2, b2, c2),
		  _Resonator(a3, b3, c3),
		  _Resonator(a4, b4, c4),
		  _Resonator(a5, b5, c5),
		  _Resonator(a6, b6, c6)
		 ),
		 _Resonator(agp, bgp, cgp),
		 _Resonator(ags, bgs, cgs),
		 _Resonator(anp, bnp, cnp),
		 _AntiResonator(agz, bgz, cgz),
		 _AntiResonator(anz, bnz, cnz)
		)
		
	def _getNoise(self):
		self._noise = random.uniform(-0.00001, 0.00001) + self._noise
		return self._noise
		
	def generateSilence(self, milliseconds):
		self._noise = 0.0
		return (0,) * (milliseconds * 10)
		
	def synthesize(self, parameters, f0):
		half_f0 = f0 / 2.0
		(fgp, fgz, fgs, fnp, fnz,
		 f1, f2, f3, f4, f5, f6,
		 bgp, bgz, bgs, bnp, bnz,
		 bw1, bw2, bw3, bw4, bw5, bw6,
		 a2, a3, a4, a5, a6,
		 ab, ah, af, av, avs,
		 milliseconds) = parameters
		
		(cascade_resonators, parallel_resonators,
		 glottal_pole_resonator, glottal_sine_resonator,
		 nasal_pole_resonator, glottal_antiresonator,
		 nasal_antiresonator) = self._initSynthesizers(
		  (fgp, fgz, fgs, fnp, fnz, f1, f2, f3, f4, f5, f6),
		  (bgp, bgz, bgs, bnp, bnz, bw1, bw2, bw3, bw4, bw5, bw6)
		 )
		
		sounds = []
		last_result = 0
		period_index = 0
		for t in xrange(milliseconds * 10):
			noise = self._getNoise()
			
			#Apply linear f0 approximation.
			pulse = 0.0
			if period_index >= f0:
				pulse = 1.0
				period_index = 0
			else:
				period_index += 2
				
			source = glottal_pole_resonator.resonate(pulse)
			source = (glottal_antiresonator.resonate(source) * av) + (glottal_sine_resonator.resonate(source) * avs)
			source += noise * ah
			source = nasal_pole_resonator.resonate(source)
			source = nasal_antiresonator.resonate(source)
			frication = noise * af
			
			result = frication * ab
			for ((cascade_resonator, parallel_resonator), amplitude) in reversed(zip(zip(cascade_resonators[1:], parallel_resonators), (a2, a3, a4, a5, a6))):
				source = cascade_resonator.resonate(source)
				result += parallel_resonator.resonate(frication * amplitude)
			result += cascade_resonators[0].resonate(source)
			
			output = int((result - last_result) * 32767.0)
			last_result = result
			while abs(output) >= 32767:
				output /= 3
			sounds.append(output)
		return tuple(sounds)
		
class _Resonator(object):
	_a = None
	_b = None
	_c = None
	_delay_1 = 0.0
	_delay_2 = 0.0
	
	def __init__(self, a, b, c):
		self._a = a
		self._b = b
		self._c = c
		
	def reset(self):
		self._p1 = self._p2 = 0.0
		
	def _resonate(self, input):
		output = self._a * input + self._b * self._delay_1 + self._c * self._delay_2
		self._delay_2 = self._delay_1
		return output
		
	def resonate(self, input):
		output = self._resonate(input)
		self._delay_1 = output
		return output
		
class _AntiResonator(_Resonator):
	def __init__(self, a, b, c):
		a = 1.0 / a
		_Resonator.__init__(self, a, -b * a, -c * a)
		
	def resonate(self, input):
		output = self._resonate(input)
		self._delay_1 = input
		return output
		