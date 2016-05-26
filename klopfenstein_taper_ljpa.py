# This Python file uses the following encoding: utf-8

# Implementation of the Klopfenstein taper from R. W. Klopfenstein:
# "A Transmission Line Taper of Improved Design"
# Proceedings of the IRE, 44 (1956)
# , the book "Microwave engineering" from D. M. Pozar
# and the paper from M. A. Grossberg:
# "Extremely rapid computation of the Klopfenstein impedance taper"
# Proceedings of the IEEE, 56 (1968)

# Copyright (C) 2016 Dumur Étienne
# etienne.dumur@gmail.com

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import numpy as np
from scipy.optimize import minimize, fsolve

from LJPA import LJPA

class KlopfensteinTaperLJPA(LJPA):



    def __init__(self, C, L_s, I_c, phi_s, phi_dc, phi_ac, theta_p,
                       Z_l, l, g_m, L_l, C_l,
                       theta_s = 0.):
        """
        Implementation of the Klopfenstein taper from R. W. Klopfenstein:
        "A Transmission Line Taper of Improved Design"
        Proceedings of the IRE, 44 (1956)
        , the book "Microwave engineering" from D. M. Pozar
        and the paper from M. A. Grossberg:
        "Extremely rapid computation of the Klopfenstein impedance taper"
        Proceedings of the IEEE, 56 (1968)

        ...

        Attributes
        ----------
        C : float
            Resonator capacitance in farad.
        L_s : float
            Resonator stray inductance in henry.
        I_c : float
            Critical current of the SQUID in ampere.
        phi_s : float
            Amplitude of the signal in rad.
        phi_dc : float
            DC amplitude of the pump in Φ0 unit.
        phi_ac : float
            AC amplitude of the pump in Φ0 unit.
        theta_p : float
            Phase of the pump in rad.
        Z_l : float,
            Impedance of the loaded element in ohm.
        l : float
            Length of the taper line in meter.
        g_m : float
            Magnitude of the ripple in the bandpass of the taper line.
        L_l : float
            Inductance per unit length of the taper line in henry per meter.
        C_l : float
            capacitance per unit length of the taper line in farad per meter.
        theta_s : {0.} float, optional
            Phase of the pump in rad, default is zero which implies that that\
            the signal phase is the reference.

        Raises
        ------
        ValueError
            If the parameters are not in the good type.
        """

        if type(Z_l) is not float:
            raise ValueError('Z_l parameter must be float type.')
        if type(l) is not float:
            raise ValueError('l parameter must be float type.')
        if type(g_m) is not float:
            raise ValueError('g_m parameter must be float type.')
        if type(L_l) is not float:
            raise ValueError('L_l parameter must be float type.')
        if type(C_l) is not float:
            raise ValueError('C_l parameter must be float type.')

        LJPA.__init__(self, C, L_s, I_c, phi_s, phi_dc, phi_ac, theta_p, theta_s)

        self.zl = Z_l
        self.l  = l
        self.gm = g_m
        self.cl = C_l
        self.ll = L_l



    def _phi(self, x, A, convergence=1e-7):
        """
        Return the integral of the modified Bessel function of the first kind
        by using the method explain by M. A. Grossberg in
        "Extremely rapid computation of the Klopfenstein impedance taper"
        Proceedings of the IEEE, 56 (1968).

        Parameters
        ----------
        convergence : float
            Value at which the method stop to refine the result of phi.
        """

        a   = 1.
        b   = 0.5*x
        phi = b
        k   = 1.

        def condition(phi, a, b):

            if type(b) is float:
                if b == 0:
                    return convergence/10.
                else:
                    return abs(1. - (phi + a*b)/phi)
            else:
                return abs(1. - (phi + a*b)/phi).all()

        while condition(phi, a, b) > convergence:

            a = A**2./(4.*k*(k + 1.))*a
            b = (x*(1 - x**2.)**k/2. + 2.*k*b)/(2*k + 1.)
            phi += a*b
            k   += 1.

        return phi



    def A(self):
        """
        Return maximum magnitude of reflection coefficient in the pass band.
        """

        y = self.g0()/self.gm
        if y < 1.:
            raise ValueError('g0/gm must be higher than 1.')

        return np.arccosh(self.g0()/self.gm)



    def g0(self, z0=50.):
        """
        Return the reflection coeficient at zero frequency.

        Parameters
        ----------
        z0 : {50.} float optional
            Impedance of the incoming transmission line.
        """

        return abs(self.zl - z0)/(self.zl + z0)



    def beta(self, f):
        """
        Return the wave vector of the taper line.

        Parameters
        ----------
        f : float, np.ndarray
            Frequency in GHz
        """

        return 2.*np.pi*f*np.sqrt(self.cl*self.ll)



    def characteristic_impedance(self, z, z0=50.):
        """
        Return the characteristic impedance of the tapper along its length.

        Parameters
        ----------
        z : float, np.ndarray
            Length position along the taper in meter.
            z must be higher than 0 and lower than the taper length.
        z0 : {50.} float optional
            Impedance of the incoming transmission line.

        Raises
        ------
        ValueError
            If z is not in the good range.
        """

        if (z < 0.).any():
            raise ValueError('z must be greater than 0')
        if (z > self.l).any():
            raise ValueError('z must be smaller than the tapper length: '+self.l)

        y = np.exp(np.log(z0*self.zl)/2.\
                      + self.g0()*self.A()**2.*self._phi(2.*z/self.l - 1., self.A())\
                        /np.cosh(self.A()))

        if z0 > self.zl:
            return y[::-1]
        else:
            return y



    def reflection_theory(self, f):
        """
        Return the theoritical reflection of the taper.
        As a theoriticalk result this reflection doesn't take into account the
        impedance of the LJPA.

        Parameters
        ----------
        f : float, np.ndarray
            Frequency in GHz.
        """

        v = (self.beta(f)*self.l)**2. - self.A()**2.

        if type(f) is float:
            if v < 0:
                c = np.cosh(np.sqrt(self.A()**2. - (self.beta(f)*self.l)**2.))
            else:
                c = np.cos(np.sqrt((self.beta(f)*self.l)**2. - self.A()**2.))
        else:
            c = np.ones_like(v)
            c[v<0] = np.cosh(np.sqrt(self.A()**2. - (self.beta(f[v<0])*self.l)**2.))
            c[v>0] = np.cos(np.sqrt((self.beta(f[v>0])*self.l)**2. - self.A()**2.))

        return self.gm*np.exp(-1j*self.beta(f)*self.l)*c



    def find_ll_cl(self, z):
        """
        Quick and dirty method to find correct inductance and capacitance per
        unit length which give a target z impedance.
        This is used by the reflection method because of the wave vector
        calculation.

        Parameters
        ----------
        z : np.ndarray
            Target impedance in ohm.
        """

        def func(x0, z):

            ll, cl = abs(x0)

            return ((np.sqrt(ll/cl) - z)/z)**2

        temp = []
        for i in z:

            temp.append(abs(minimize(func,
                                 [self.ll, self.cl],
                                 args=(i,),
                                 method='Nelder-Mead').x))

        temp = np.array(temp)

        return temp[:,0], temp[:,1]




    def reflection(self, f, n=1e2):
        """
        Return the reflection of the taper.
        To do so, the taper impedance is discretised in n sections.
        Each of these sections is modeled as a lossless transmission line.
        At the end the LJPA is modeled as a lumped element to ground and very
        high impedance (1e99 ohm) to the line.

        Because of matrix product this method is quite slow...
        If somebody has an idea to improve it, don't hesitate.

        Parameters
        ----------
        f : float, np.ndarray
            Frequency in GHz.
        n : {0.} float, optional
            Number of discret elements used to model the taper line.
        """

        # Calculate the different characteristic impedance of the different
        # part of the transnmission line
        z = self.characteristic_impedance(np.linspace(0., self.l, n))

        # Calculate the corresponding L_l and C_l for the elements
        ll, cl = self.find_ll_cl(z)

        result = []
        if type(f) is not np.ndarray:
            f = [f]
        for f in f:

            a = 2.*np.pi*f*np.sqrt(ll[0]*cl[0])*self.l/(n-1)
            z = np.sqrt(ll[0]/cl[0])
            c = np.cos(a)
            s = np.sin(a)

            # We matrix multiply all the elements
            M = np.array([[c,         1j*z*s],
                          [1j/z*s, c]])
            for lll, ccl in zip(ll[1:], cl[1:]):

                z = np.sqrt(lll/ccl)
                # print z
                a = 2.*np.pi*f*np.sqrt(lll*ccl)*self.l/(n-1)

                c = np.cos(a)
                s = np.sin(a)

                M = M.dot(np.array([[c,       1j*z*s],
                                    [1j/z*s, c]]))

            # We end the chain by two elements:
            # 1 - a load impedance to the ground
            # 2 - a huge impedance to the circuit
            M = M.dot(np.array([[1., 0.],[1./self.impedance(f), 1.]]))
            M = M.dot(np.array([[1., 1e99],[0., 1.]]))

            # Compute the reflection fro the array element
            a = M.item(0)
            b = M.item(1)
            c = M.item(2)
            d = M.item(3)

            nu = a + b/50. - c*50. - d
            de = a + b/50. + c*50. + d

            result.append(nu/de)

        return np.array(result)