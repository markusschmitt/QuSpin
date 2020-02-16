import numpy as _np
from scipy.linalg.blas import get_blas_funcs
from scipy.linalg import eigh_tridiagonal
from copy import deepcopy


__all__ = ["lanczos_full","lanczos_iter","lin_comb_Q"]


def _lanczos_vec_iter_core(A,v0,a,b):
	dtype = _np.result_type(A.dtype,v0.dtype)

	q = v0.astype(dtype,copy=True)

	q_norm = _np.linalg.norm(q)
	if _np.abs(q_norm-1.0) > _np.finfo(dtype).eps:
			_np.divide(q,q_norm,out=q)

	q_view = q[:]
	q_view.setflags(write=0,uic=0)

	yield q_view # return non-writable array

	m = a.size
	n = q.size
	axpy = get_blas_funcs('axpy', arrays=(q,))

	v = _np.zeros_like(v0,dtype=dtype)
	r = _np.zeros_like(v0,dtype=dtype)

	try:
		A.dot(q,out=r)
		use_out = True
	except TypeError:
		r[:] = A.dot(q)
		use_out = False

	axpy(q,r,n,-a[0])

	for i in range(1,m,1):
		v[:] = q[:]

		_np.divide(r,b[i-1],out=q)

		yield q_view # return non-writable array

		if use_out:
			A.dot(q,out=r)
		else:
			r[:] = A.dot(q)

		axpy(v,r,n,-b[i-1])
		axpy(q,r,n,-a[i])


class _lanczos_vec_iter(object):
	def __init__(self,A,v0,a,b):
		self._A = A
		self._v0 = v0
		self._a = a
		self._b = b

	def __iter__(self):
		return _lanczos_vec_iter_core(self._A,self._v0,self._a,self._b)



def lanczos_full(A,v0,m,full_ortho=False,out=None,eps=None):
	""" Creates Lanczos basis; diagonalizes Krylov subspace in Lanczos basis.

	Given a hermitian matrix `A` of size :math:`n\\times n` and an integer `m`, the Lanczos algorithm computes 
	
	* an :math:`n\\times m` matrix  :math:`Q`, and 
	* a real symmetric tridiagonal matrix :math:`T=Q^\\dagger A Q` of size :math:`m\\times m`. The matrix :math:`T` can be represented via its eigendecomposition `(E,V)`: :math:`T=V\\mathrm{diag}(E)V^T`. 
	This function computes the triple :math:`(E,V,Q^T)`.

	:red:`NOTE:` This function returns :math:`Q^T;\\,Q^T` is (in general) different from :math:`Q^\\dagger`.

 
	Notes
	-----
	
	* performs classical lanczos algorithm for hermitian matrices and cannot handle degeneracies when calculating eigenvalues. 
	* the function allows for full orthogonalization, see `full_ortho`. The resulting :math:`T` will not neccesarily be tridiagonal.
	* `V` is always real-valued, since :math:`T` is real and symmetric.
	* `A` must have a 'dot' method to perform calculation, 
	* The 'out' argument to pass back the results of the matrix-vector product will be used if the 'dot' function supports this argument.

	Parameters
	-----------
	A : LinearOperator, hamiltonian, np.ndarray, or object with a 'dot' method and a 'dtype' method.
		Python object representing a linear map to compute the Lanczos approximation to the largest eigenvalues/vectors of. Must contain a dot-product method, used as `A.dot(v)` and a dtype method, used as `A.dtype`, e.g. `hamiltonian`, `quantum_operator`, `quantum_LinearOperator`, sparse or dense matrix.
	v0 : array_like, (m,)
		initial vector to start the Lanczos algorithm from.
	m : int
		Number of Lanczos vectors (size of the Krylov subspace)
	full_ortho : bool, optional
		perform a QR decomposition on Q_T generated from the standard lanczos iteration to remove any loss of orthogonality due to numerical precision.
	out : np.ndarray, optional
		Array to store the Lanczos vectors in (e.g. `Q`). in memory efficient way.
	eps : float, optional
		Used to cutoff lanczos iteration when off diagonal matrix elements of `T` drops below this value. 

	Returns
	--------
	tuple(E,V,Q_T)
		* E : (m,) numpy.ndarray: eigenvalues of Krylov subspace tridiagonal matrix :math:`T`.
		* V : (m,m) numpy.ndarray: eigenvectors of Krylov subspace tridiagonal matrix :math:`T`.
		* Q_T : (m,n) numpy.ndarray: matrix containing the `m` Lanczos vectors. This is :math:`Q^T` (not :math:`Q^\\dagger`)!

	Examples
	--------

	>>> E, V, Q_T = lanczos_full(H,v0,20)


	
	"""


	dtype = _np.result_type(A.dtype,v0.dtype)

	if v0.ndim != 1:
		raise ValueError

	n = v0.size

	if out is not None:
		if out.shape != (m,n):
			raise ValueError
		if out.dtype != dtype:
			raise ValueError
		if not out.flags["CARRAY"]:
			raise ValueError

		Q = out
	else:
		Q = _np.zeros((m,n),dtype=dtype)

	Q[0,:] = v0[:]
	v = _np.zeros_like(v0,dtype=dtype)
	r = _np.zeros_like(v0,dtype=dtype)

	b = _np.zeros((m,),dtype=v.real.dtype)
	a = _np.zeros((m,),dtype=v.real.dtype)

	# get function : y <- y + a * x
	axpy = get_blas_funcs('axpy', arrays=(r, v))

	if eps is None:
		eps = _np.finfo(dtype).eps

	q_norm = _np.linalg.norm(Q[0,:])

	if _np.abs(q_norm-1.0) > eps:
		_np.divide(Q[0,:],q_norm,out=Q[0,:])
	
	try:
		A.dot(Q[0,:],out=r) # call if operator supports 'out' argument
		use_out  = True
	except TypeError:
		r[:] = A.dot(Q[0,:])
		use_out = False

	a[0] = _np.vdot(Q[0,:],r).real

	axpy(Q[0,:],r,n,-a[0])
	b[0] = _np.linalg.norm(r)

	i = 0
	for i in range(1,m,1):
		v[:] = Q[i-1,:]

		_np.divide(r,b[i-1],out=Q[i,:])

		if use_out:
			A.dot(Q[i,:],out=r) # call if operator supports 'out' argument
		else:
			r[:] = A.dot(Q[i,:])

		axpy(v,r,n,-b[i-1])

		a[i] = _np.vdot(Q[i,:],r).real
		axpy(Q[i,:],r,n,-a[i])

		b[i] = _np.linalg.norm(r)
		if b[i] < eps:
			m = i
			break


	if full_ortho:
		q,_ = _np.linalg.qr(Q[:i+1].T)

		Q[:i+1,:] = q.T[...]

		h = _np.zeros((m,m),dtype=a.dtype)

		for i in range(m):
			if use_out:
				A.dot(Q[i,:],out=r) # call if operator supports 'out' argument
			else:
				r[:] = A.dot(Q[i,:])

			_np.conj(r,out=r)
			h[i,i:] = _np.dot(Q[i:,:],r).real

		E,V = _np.linalg.eigh(h,UPLO="U")

	else:
		E,V = eigh_tridiagonal(a[:m],b[:m-1])


	return E,V,Q[:m]


def lanczos_iter(A,v0,m,return_vec_iter=True,copy_v0=True,copy_A=False,eps=None):
	""" Creates generator for Lanczos basis; diagonalizes Krylov subspace in Lanczos basis.

	Given a hermitian matrix `A` of size :math:`n\\times n` and an integer `m`, the Lanczos algorithm computes 
	
	* an :math:`n\\times m` matrix  :math:`Q`, and 
	* a real symmetric tridiagonal matrix :math:`T=Q^\\dagger A Q` of size :math:`m\\times m`. The matrix :math:`T` can be represented via its eigendecomposition `(E,V)`: :math:`T=V\\mathrm{diag}(E)V^T`. 
	This function computes the triple :math:`(E,V,Q^T)`.

	:red:`NOTE:` This function returns :math:`Q^T;\\,Q^T` is (in general) different from :math:`Q^\\dagger`.
 

	Parameters
	-----------
	A : LinearOperator, hamiltonian, np.ndarray, etc. with a 'dot' method and a 'dtype' method.
		Python object representing a linear map to compute the Lanczos approximation to the largest eigenvalues/vectors of. Must contain a dot-product method, used as `A.dot(v)` and a dtype method, used as `A.dtype`, e.g. `hamiltonian`, `quantum_operator`, `quantum_LinearOperator`, sparse or dense matrix.
	v0 : array_like, (m,)
		initial vector to start the Lanczos algorithm from.
	m : int
		Number of Lanczos vectors (size of the Krylov subspace)
	return_vec_iter : bool, optional
		Toggles whether or not to return the Lanczos basis iterator.
	copy_v0 : bool, optional
		Whether or not to produce of copy of initial vector `v0`.
	copy_A : bool, optional
		Whether or not to produce of copy of linear operator `A`.
	eps : float, optional
		Used to cutoff lanczos iteration when off diagonal matrix elements of `T` drops below this value. 

	Returns
	--------
	tuple(E,V,Q_T)
		* E : (m,) numpy.ndarray: eigenvalues of Krylov subspace tridiagonal matrix :math:`T`.
		* V : (m,m) numpy.ndarray: eigenvectors of Krylov subspace tridiagonal matrix :math:`T`.
		* Q_T : generator that yields the `m` lanczos basis vectors on the fly, produces the same result as: :code:`iter(Q_T[:])` where `Q_T` is the array generated by `lanczos_full`

 	Notes
 	-----
 	* this function is useful to minimize any memory requirements in the calculation of the Lanczos basis. 
 	* the generator of the lanczos basis performs the calculation 'on the fly'. This means that the lanczos iteration is repeated every time this generator is looped over. 
 	* this generator `Q_T` can be reused as many times as needed, this relies on the data in both `v0` and `A` remaining unchanged during runtime. If this cannot be guaranteed then it is safer to set both `copy_v0` and `copy_A` to be true. 
 	* `V` is always real-valued, since :math:`T` is real and symmetric.


	Examples
	--------

	>>> E, V, Q_iterator = lanczos_iter(H,v0,20)

	"""

	if copy_v0 and return_vec_iter:
		v0 = v0.copy()

	if copy_A and return_vec_iter:
		A = deepcopy(A)

	if v0.ndim != 1:
		raise ValueError("expecting array with ndim=1 for initial Lanczos vector.")

	dtype = _np.result_type(A.dtype,v0.dtype)

	q = v0.astype(dtype,copy=True)
	v = _np.zeros_like(v0,dtype=dtype)
	r = _np.zeros_like(v0,dtype=dtype)

	n = v0.size

	b = _np.zeros((m,),dtype=q.real.dtype)
	a = _np.zeros((m,),dtype=q.real.dtype)

	# get function : y <- y + a * x
	axpy = get_blas_funcs('axpy', arrays=(q, v))

	if eps is None:
		eps = _np.finfo(dtype).eps

	q_norm = _np.linalg.norm(q)

	if _np.abs(q_norm-1.0) > eps:
		_np.divide(q,q_norm,out=q)

	try:
		A.dot(q,out=r) # call if operator supports 'out' argument
		use_out = True
	except TypeError:
		r[:] = A.dot(q)
		use_out = False

	a[0] = _np.vdot(q,r).real
	axpy(q,r,n,-a[0])
	b[0] = _np.linalg.norm(r)

	i = 0
	for i in range(1,m,1):
		v[:] = q[:]

		_np.divide(r,b[i-1],out=q)

		if use_out:
			A.dot(q,out=r) # call if operator supports 'out' argument
		else:
			r[:] = A.dot(q)

		axpy(v,r,n,-b[i-1])
		a[i] = _np.vdot(q,r).real
		axpy(q,r,n,-a[i])

		b[i] = _np.linalg.norm(r)
		if b[i] < eps:
			break

	a = a[:i+1].copy()
	b = b[:i].copy()
	del q,r,v

	E,V = eigh_tridiagonal(a,b)

	if return_vec_iter:
		return E,V,_lanczos_vec_iter(A,v0,a.copy(),b.copy())
	else:
		return E,V


def _get_first_lv_iter(r,Q_iter):
	yield r
	for Q in Q_iter:
		yield Q


def _get_first_lv(Q_iter):
	r = next(Q_iter)
	return r,_get_first_lv_iter(r,Q_iter)


# I suggest the name `lv_average()` or `lv_linearcomb` or `linear_combine_Q()` instead of `lin_comb_Q()`
def lin_comb_Q(coeff,Q,out=None):
	""" Computes a linear combination of the Lanczos basis vectors:

	.. math::
		v_j = \\sum_{j=1}^{m} c_i Q_{ij} 

	
	Parameters
	-----------
	coeff : (m,) array_like
		list of coefficients to compute the linear combination of Lanczos basis vectors with.
	Q : (m,n) np.ndarray, generator
		Lanczos basis vectors or a generator for the Lanczos basis.
	out : (n,) np.ndarray, optional
		Array to store the result in.
	
	Returns
	--------
	(n,) np.ndarray
		Linear combination :math:`v` of Lanczos basis vectors. 

	Examples
	--------

	>>> v = lin_comb_Q(coeff,Q)

	"""


	coeff = _np.asanyarray(coeff)

	if isinstance(Q,_np.ndarray):
		Q_iter = iter(Q[:])
	else:
		Q_iter = iter(Q)

	q = next(Q_iter)

	dtype = _np.result_type(q.dtype,coeff.dtype)

	if out is not None:
		if out.shape != q.shape:
			raise ValueError("'out' must have same shape as a Lanczos vector.")
		if out.dtype != dtype:
			raise ValueError("dtype for 'out' does not match dtype for result.")
		if not out.flags["CARRAY"]:
			raise ValueError("'out' must be a contiguous array.")
	else:
		out = _np.zeros(q.shape,dtype=dtype)

	# get function : y <- y + a * x
	axpy = get_blas_funcs('axpy', arrays=(out,q))	
	
	n = q.size

	_np.multiply(q,coeff[0],out=out)
	for weight,q in zip(coeff[1:],Q_iter):
		axpy(q,out,n,weight)

	return out
