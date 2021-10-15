"""Neural network layer classes."""
import itertools
import numpy as np


class Layer:
    """
    Base layer class.
    
    Parameters
    ----------
    input_size : tuple
        size of the layer input
    output_size : tuple
        size of the layer output
    activation : str or None
        activation function name
    input_index_transformer : IndexTransformer or None
        transform indexes from this layer index to the input layer index size
    """
    def __init__(self, input_size, output_size, *, activation=None, input_index_transformer=None):
        assert isinstance(input_size, list)
        assert isinstance(output_size, list)
        self.__input_size = input_size
        self.__output_size = output_size
        self.__activation = activation
        self.__input_index_transformer = input_index_transformer

    @property
    def input_size(self):
        return self.__input_size

    @property
    def output_size(self):
        return self.__output_size

    @property
    def activation(self):
        return self.__activation

    @property
    def input_index_transformer(self):
        return self.__input_index_transformer

    @property
    def input_indexes_with_input_layer_indexes(self):
        if self.__input_index_transformer is None:
            for index in self.input_indexes:
                yield index, index
        else:
            transformer = self.__input_index_transformer
            for index in self.input_indexes:
                yield index, transformer(index)

    @property
    def input_indexes(self):
        return itertools.product(*[range(v) for v in self.__input_size])

    @property
    def output_indexes(self):
        return itertools.product(*[range(v) for v in self.__output_size])

    def eval(self, x):
        if self.__input_index_transformer is not None:
            x = np.reshape(x, self.__input_index_transformer.output_size)
        assert x.shape == tuple(self.input_size)
        y = self._eval(x)
        return self._apply_activation(y)

    def __repr__(self):
        return f"<{str(self)} at {hex(id(self))}>"

    def _eval(self, x):
        raise NotImplementedError()

    def _apply_activation(self, x):
        if self.__activation == "linear" or self.__activation is None:
            return x
        elif self.__activation == "relu":
            return np.maximum(x, 0)
        elif self.__activation == "sigmoid":
            return 1.0 / (1.0 + np.exp(-x))
        else:
            raise ValueError(f"Unknown activation function {self.__activation}")


class InputLayer(Layer):
    """
    The first layer in any network.
    """
    def __init__(self, size):
        super().__init__(size, size)

    def __str__(self):
        return f"InputLayer(input_size={self.input_size}, output_size={self.output_size})"

    def _eval(self, x):
        return x


class DenseLayer(Layer):
    """
    Dense layer.
    """
    def __init__(self, input_size, output_size, weights, biases, *, activation=None, input_index_transformer=None):
        super().__init__(input_size, output_size, activation=activation, input_index_transformer=input_index_transformer)
        self.__weights = weights
        self.__biases = biases

    @property
    def weights(self):
        return self.__weights

    @property
    def biases(self):
        return self.__biases

    def __str__(self):
        return f"DenseLayer(input_size={self.input_size}, output_size={self.output_size})"

    def _eval(self, x):
        y = np.dot(x, self.__weights) + self.__biases
        assert y.shape == tuple(self.output_size)
        return y


class ConvLayer(Layer):
    def __init__(self, input_size, output_size, strides, kernel, *, activation=None, input_index_transformer=None):
        super().__init__(input_size, output_size, activation=activation, input_index_transformer=input_index_transformer)
        self.__strides = strides
        self.__kernel = kernel

    def kernel_with_input_indexes(self, out_d, out_r, out_c):
        [_, kernel_d, kernel_r, kernel_c] = self.__kernel.shape
        [rows_stride, cols_stride] = self.__strides
        start_in_d = 0
        start_in_r = out_r * rows_stride
        start_in_c = out_c * cols_stride
        transform = lambda x: x
        if self.input_index_transformer is not None:
            transform = self.input_index_transformer

        for k_d in range(kernel_d):
            for k_r in range(kernel_r):
                for k_c in range(kernel_c):
                    k_v = self.__kernel[out_d, k_d, k_r, k_c]
                    local_index = (start_in_d + k_d, start_in_r + k_r, start_in_c + k_c)
                    yield k_v, transform(local_index)

    @property
    def strides(self):
        return self.__strides

    @property
    def kernel_shape(self):
        return self.__kernel.shape[2:]

    def __str__(self):
        return f"ConvLayer(input_size={self.input_size}, output_size={self.output_size}, strides={self.strides}, kernel_shape={self.kernel_shape})"

    def _eval(self, x):
        y = np.empty(shape=self.output_size)
        assert len(self.output_size) == 3
        [depth, rows, cols] = self.output_size
        for out_d in range(depth):
            for out_r in range(rows):
                for out_c in range(cols):
                    acc = 0.0
                    for (k, index) in self.kernel_with_input_indexes(out_d, out_r, out_c):
                        acc += k * x[index]
                    y[out_d, out_r, out_c] = acc
        return y


class IndexTransformer:
    """
    Transform indexes from one layer to the other.

    Parameters
    ----------
    input_size : tuple
        the input size
    output_size : tuple
        the transformed input layer's output size
    """
    def __init__(self, input_size, output_size):
        self.__input_size = input_size
        self.__output_size = output_size

    @property
    def input_size(self):
        return self.__input_size

    @property
    def output_size(self):
        return self.__output_size

    def __call__(self, index):
        flat_index = np.ravel_multi_index(index, self.__output_size)
        return np.unravel_index(flat_index, self.__input_size)

    def __str__(self):
        return f"IndexTransformer(input_size={self.input_size}, output_size={self.output_size})"
