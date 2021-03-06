import numpy as np
import cupy as cp

class NeuralNet:
    """
    Implements neural net
    Arguments: 
    layer_dims -- list of dimensions for each layer
    lr -- learning rate for gradient descent
    num_iterations -- number of iterations of optimization loop
    print_cost -- if True, prints cost for every 100 steps
    """
    
    
    def __init__(self, layer_dims, lr=0.0075, num_epochs=200, lambd=0.1, beta=0.9,  print_cost=True):
        
        self.layer_dims = layer_dims
        self.lr = lr
        self.num_epochs = num_epochs
        self.lambd = lambd
        self.beta = beta
        self.print_cost = print_cost
        self.trained_params = {}
        self.fitted = False
        
    
    def compute_cost(self, Y_true, Y_pred, parameters):
        """
        Arguments:
        Y_true -- vector of true labels for training set, shape(1, number of examples)
        Y_pred -- probability vector corresponding to label predictions, shape(1, number of examples)
        parameters -- dictionary containing all weights and biases
        Returns:
        cost -- cross entropy cost
        """
        m = Y_true.shape[1]  # number of examples
        L = len(parameters) // 2
        
        cross_entropy = -(1/m)*cp.sum(Y_true*cp.log(Y_pred) + (1 - Y_true)*cp.log(1-Y_pred))
        
        L2_norm = 0
        for l in range(L):
            L2_norm += cp.sum(cp.square(parameters['W' + str(l + 1)]))
            
        L2_regularization = (self.lambd/(2*m))*L2_norm
        J = cross_entropy + L2_regularization
        
        return J


    def relu(self, Z):
        """ReLU function"""
        
        A = cp.maximum(0, Z)
        assert(A.shape == Z.shape)
        
        return A
    
    def leaky_relu(self, Z):
        '''Leaky ReLU function'''
    
        A = cp.where(Z >= 0, Z, Z*0.01)
        assert(A.shape == Z.shape)
    
        return A
    
    def sigmoid(self, Z):
        """Sigmoid function"""
        return 1/(1 + cp.exp(-Z))
    
    def relu_backward(self, dA, Z):
        """
        Implement the backward propagation for a single RELU unit.
        Arguments:
        dA -- post-activation gradient, of any shape
        cache -- 'Z' where we store for computing backward propagation efficiently
        Returns:
        dZ -- Gradient of the cost with respect to Z
        """

        dZ = cp.array(dA, copy=True) # just converting dz to a correct object.

        # When z <= 0, you should set dz to 0 as well. 
        dZ[Z <= 0] = 0

        assert (dZ.shape == Z.shape)

        return dZ
    
    def lrelu_backward(self, dA, Z):
        """
        Implement the backward propagation for a single Leaky ReLU unit.
        Arguments:
        dA -- post-activation gradient, of any shape
        cache -- 'Z' where we store for computing backward propagation efficiently
        Returns:
        dZ -- Gradient of the cost with respect to Z
        """
        
        derivative = cp.where(Z >= 0, 1, 0.01)
        dZ = cp.multiply(dA, derivative)
        
        return dZ

    def sigmoid_backward(self, dA, Z):

        def sigmoid_derivative(Z):
             return cp.multiply(self.sigmoid(Z), (1 - self.sigmoid(Z)))

        dZ = cp.multiply(dA, sigmoid_derivative(Z))
        return dZ
    
    
    def init_params(self, n):
        """
        Creating random weigths and biases for all layers in NN

        Arguments:
        n -- array of numbers of units in each layer

        Returns:
        params -- dictionary of weights and biases for each layer of NN:
                  Wl -- weigths matrix of l-th layer, shape(n[l], n[l-1])
                  bl -- bias vector of l-th layer, shape(n[l], 1)
        """

        params = {}
        
        L = len(n)  # number of layers in NN

        for l in np.arange(1, L):
            params['W' + str(l)] = cp.random.randn(n[l], n[l-1])*0.001
            params['b' + str(l)] = cp.zeros((n[l], 1))
            
           
            
            assert(params['W' + str(l)].shape == (n[l], n[l - 1]))
            assert(params['b' + str(l)].shape == (n[l], 1))

        return params
    
    def init_v(self, n):
        """
        Initialize dictionary to store the exponentially weighted average of the gradient
        on previous steps for GD with momentum
        Arguments:
        n -- list with number of units in each layer
        Returns:
        v -- dictionary with values of v for weights and biases in each layer
        """
        
        v = {}
        L = len(n)
        
        for l in range(1, L):
            v['dW' + str(l)] = cp.zeros((n[l], n[l-1]))
            v['db' + str(l)] = cp.zeros((n[l], 1))
            
        return v

    def init_dropout(self, keep_prob, m):
        """
        Initializes dropout matrices.
        Arguments:
        keep_prob -- list with probabilities of keeping unit for each hidden layer
        m -- number of examples in train set
        Returns:
        D -- dictionary with dropout matrices for every hidden layer
        keep_prob -- list with probabilities of keeping unit for each hidden layer
        """
        
        D = {}
        L = len(self.layer_dims)
        
        for l in range(L):
            
            D[str(l)] = cp.random.rand(self.layer_dims[l], m)
            D[str(l)] = D[str(l)] < keep_prob[l]
            
            assert(D[str(l)].shape == (self.layer_dims[l], m))
            
        return D, keep_prob
    
    def init_mini_batches(self, X, y, mb_size=64):
        """
        Initialize mini batches of data with given size
        Arguments:
        X -- train data(pandas DataFrame)
        y -- true labels of data X(pandas Series)
        mb_size -- mini batch size
        Return:
        mini_batches -- list of tuples(X_mini_batch, y_mini_batch)
        """
        
        m = X.shape[1]
        mini_batches = []
        
        permutation = list(np.random.permutation(X.columns))
        shuffled_X = X.loc[:, permutation].to_numpy()
        shuffled_X = cp.array(shuffled_X)
        shuffled_y = y[permutation].to_numpy().reshape((1,m))
        shuffled_y = cp.array(shuffled_y)
        
        num_batches = int(cp.floor(m/mb_size))
        
        for n in range(num_batches):
            mini_batch_X = shuffled_X[:, n*mb_size:(n + 1)*mb_size]
            mini_batch_y = shuffled_y[:, n*mb_size:(n + 1)*mb_size]
            mini_batch = (mini_batch_X, mini_batch_y)
            mini_batches.append(mini_batch)
            
        if m % mb_size != 0:
            mini_batch_X = shuffled_X[:,num_batches * mb_size:]
            mini_batch_y = shuffled_y[:,num_batches * mb_size:]
            mini_batch = (mini_batch_X, mini_batch_y)
            mini_batches.append(mini_batch)
            
        return mini_batches
        
    
    def L_model_forward(self, X, parameters, dropout_params, mode):
        """
        Implements forward propagation part of L layer Neural Net
        Arguments:
        X -- input data
        parameters -- dictionary with weights and biases for every layer
        Returns:
        AL -- activations from the last layer
        caches -- linear caches for every layer
        """
        
        def linear_forward(A_prev, W, b):
            """
            Linear part of forward propagation.
            Arguments:
            A_prev -- activations from previous layer or input(X)
            W -- weights for current layer
            b -- biases for current layer
            Returns:
            Z -- the input for the activation function
            cache -- dictionary containing A_prev, W and b

            """

            Z = cp.dot(W, A_prev) + b
            
            assert(Z.shape == (W.shape[0], A.shape[1]))
            cache = (A_prev, W, b)

            return Z, cache
        
        def activation_forward(A_prev, W, b, activation):
            """
            Forward propagation for activation part of layer
            Arguments:
            A_prev -- activations from previous layer or input(X)
            W -- weights for current layer
            b -- biases for current layer
            activtion -- activation function to use in this layer
            Returns:
            A -- activations from this layer
            cache -- tuple containing values of A_prev and calculated in this layer W, b, Z
            """

            Z, linear_cache = linear_forward(A_prev, W, b)

            if activation == 'ReLU':
                A = self.relu(Z)
                
            elif activation == 'Sigmoid':
                A = self.sigmoid(Z)
                
            elif activation == 'Leaky ReLU':
                A = self.leaky_relu(Z)

            assert (A.shape == (W.shape[0], A_prev.shape[1]))
            cache = (linear_cache, Z)

            return A, cache
        
        if mode == 'train':
            D, keep_prob = dropout_params
            
        caches = []
        A = X

        L = len(parameters)//2

        for l in range(1, L):
            
            A_prev = A
            A, cache = activation_forward(A_prev, parameters['W' + str(l)], parameters['b' + str(l)], 'Leaky ReLU')
            
            if mode == 'train':
                A = cp.multiply(A, D[str(l)])
                A /= keep_prob[l]
                
            caches.append(cache)
            
            """
            print('{} layer forwardpropagated'.format(l))
            print('A_prev shape: {}'.format(cache[0][0].shape))
            print('W shape: {}'.format(cache[0][1].shape))
            print('b shape: {}'.format(cache[0][2].shape))
            """
        AL, cache = activation_forward(A, parameters['W' + str(L)], parameters['b' + str(L)], 'Sigmoid')
        
        if mode == 'train':
            AL = cp.multiply(AL, D[str(L)])
            AL /= keep_prob[L]
            
        caches.append(cache)
        """
        print('{} layer forwardpropagated'.format(L))
        print('A_prev shape: {}'.format(cache[0][0].shape))
        print('W shape: {}'.format(cache[0][1].shape))
        print('b shape: {}'.format(cache[0][2].shape))
        """
        
        assert(AL.shape == (1, X.shape[1]))

        return AL, caches
    
    
    def L_model_backward(self, AL, Y, caches, dropout_params):
        """
        Implements backward propagation part of L layer Neural Net
        Arguments:
        AL -- activation of the last layer
        Y -- true labels for data X
        caches -- list of caches for every layer
        Returns:
        grads -- A dictionary with the gradients
                 grads["dA" + str(l)] = ... 
                 grads["dW" + str(l)] = ...
                 grads["db" + str(l)] = ... 
        """
        def linear_back(dZ, cache):
            """
            Back propagation for linear section of layer
            Arguments:
            dZ -- Gradient of the cost function w.r.t linear output of current layer
            cache -- tuple of A_prev, W, b values used in this layer
            Returns:
            dA_prev -- Gradient of the co w.r.t activations fom previous layer
            dW -- Gradient of the cost w.r.t weights
            db -- Gradient of the cost w.r.t biases
            """

            A_prev, W, b = cache
            m = A_prev.shape[1]

            dW = cp.dot(dZ, A_prev.T)/m + (self.lambd * W)/m
            db = cp.sum(dZ, axis=1, keepdims=True)/m
            dA_prev = cp.dot(W.T, dZ)
            
            assert (dA_prev.shape == A_prev.shape)
            assert (dW.shape == W.shape)

            return dA_prev, dW, db
        

        def activation_back(dA, cache, activation):
            """
            Backpropagation for the activation part of the current layer
            Arguments:
            dA -- Gradient wrt activations of the current layer
            cache -- A_prev, W, b, Z for current layer
            activation -- activation function to use in this layer
            Returns:
            dA_prev -- Gradient of the cost wrt the activation of the previous layer
            dW -- Gradient of the cost wrt W (current layer l), same shape as W
            db -- Gradient of the cost wrt b (current layer l), same shape as b
            """

            linear_cache, Z = cache

            if activation == 'ReLU':
                dZ = self.relu_backward(dA, Z)
                #print("dZ shape: {}".format(dZ.shape))
            elif activation == 'Sigmoid':
                dZ = self.sigmoid_backward(dA, Z)
                #print("dZ shape: {}".format(dZ.shape))
            elif activation == 'Leaky ReLU':
                dZ = self.lrelu_backward(dA, Z)
            

            dA_prev, dW, db = linear_back(dZ, linear_cache)
            #print('db shape: {}'.format(db.shape))
            #print('dW shape: {}'.format(dW.shape))

            return dA_prev, dW, db
        
        D, keep_prob = dropout_params
        grads = {}
        L = len(caches)
        Y = Y.reshape(AL.shape)
        m = AL.shape[1]

        dAL = -(cp.divide(Y, AL) - cp.divide(1 - Y, 1 - AL))
        dAL = cp.multiply(dAL, D[str(L)])
        dAL /= keep_prob[L]

        grads['dA' + str(L)], grads['dW' + str(L)], grads['db' + str(L)] = activation_back(dAL,
                                                                                           caches[-1],
                                                                                           'Sigmoid')
        #print("Last layer backpropagated")

        for l in reversed(range(L-1)):
            grads['dA' + str(l+1)], grads['dW' + str(l+1)], grads['db' + str(l+1)] = activation_back(grads['dA' + str(l+2)],
                                                                                               caches[l],
                                                                                               'Leaky ReLU')
            grads['dA' + str(l+1)] = cp.multiply(grads['dA' + str(l+1)], D[str(l)])
            grads['dA' + str(l+1)] /= keep_prob[l+1]
            
            #print("{} layer backpropagated".format(l+1))
        return grads
    

    def update_params(self, parameters, grads, v, lr):
        """
        Updates parametrs using gradient descent
        Arguments:
        parameters -- dictionary with parameters for every layer
        grads -- dictionary with gradients for every layer
        lr -- learning rate for gradient descent
        v -- dictionary with the exponentially weighted averages of the gradient for W and b in each layer
        Returns:
        parameters -- dictionary with updated parameters
        v -- dictionary with updated Vs
        """

        L = len(parameters) // 2

        for l in range(L):
            
            v['dW' + str(l+1)] = self.beta*v['dW' + str(l+1)] + (1 - self.beta)*grads['dW' + str(l+1)]
            v["db" + str(l+1)] = self.beta*v["db" + str(l+1)] + (1 - self.beta)*grads['db' + str(l+1)]
            
            parameters['W' + str(l+1)] -= v['dW' + str(l+1)]*lr
            parameters['b' + str(l+1)] -= v['db' + str(l+1)]*lr

        return parameters, v
    
    
    def fit(self, X_train, Y_train, mb_size=64):
        """
        Trains the NN for classification
        Arguments:
        X_train -- train data
        Y_train -- true labels for train data
        """
        
        parameters = self.init_params(self.layer_dims)
        v = self.init_v(self.layer_dims)
        mini_batches = self.init_mini_batches(X_train, Y_train, mb_size)
        costs = []
        
        for i in range(self.num_epochs):
            
            for b in range(len(mini_batches)):
                
                X_train, Y_train = mini_batches[b]
                
                dropout_params = self.init_dropout(keep_prob, X_train.shape[1])
                
                AL, caches = self.L_model_forward(X_train, parameters, mode='train', dropout_params=dropout_params)
                cost = self.compute_cost(Y_train, AL, parameters)
                grads = self.L_model_backward(AL, Y_train, caches, dropout_params)
                
                parameters, v = self.update_params(parameters, grads, v, self.lr)
            
            if self.print_cost and i % 10 == 0:
                print('Cost after ' + str(i + 1) + 'th epoch: {}'.format(cost))
                costs.append(cost)
            
        plt.plot(costs)
        plt.xlabel("Epochs (per tens)")
        plt.ylabel("Cost")
        plt.title(f"Cost curve for the learning rate = {self.lr}")
        
        self.trained_params = parameters
        self.fitted = True
        return parameters
            
    def predict(self, X):
        """
        This function is used to predict the results of a  L-layer neural network.
        Arguments:
        X -- data set of examples you would like to label
        parameters -- parameters of the trained model
        Returns:
        p -- predictions for the given dataset X
        """

        m = X.shape[1]
        y = np.zeros((1,m))

        # Forward propagation
        probas, caches = self.L_model_forward(X, self.trained_params, mode='test', dropout_params=[0,0])


        # convert probas to 0/1 predictions
        for i in range(probas.shape[1]):
            if probas[0,i] > 0.5:
                y[0,i] = 1
            else:
                y[0,i] = 0

        return y, probas
