import numpy as np
from numpy import exp
from numpy.linalg import inv

class BPIC(object):
    # constants
    # BSO
    BSO_MEAN_INIT_NO     = 0;
    BSO_MEAN_INIT_MMSE   = 1;
    BSO_MEAN_INIT_MRC    = 2;        # in Alva's paper, he calls this matched filter
    BSO_MEAN_INIT_ZF     = 3;        # x_hat=inv(H'*H)*H'*y (this requires y.len >= x.len)
    BSO_MEAN_INIT_TYPES  = [BSO_MEAN_INIT_NO, BSO_MEAN_INIT_MMSE, BSO_MEAN_INIT_MRC, BSO_MEAN_INIT_ZF];
    BSO_MEAN_CAL_MRC = 1;
    BSO_MEAN_CAL_ZF = 2;
    BSO_MEAN_CAL_TYPES = [BSO_MEAN_CAL_MRC, BSO_MEAN_CAL_ZF];
    BSO_VAR_APPRO   = 1;        # use approximated variance
    BSO_VAR_ACCUR   = 2;        # use accurate variance (will update in the iterations)
    BSO_VAR_TYPES   = [BSO_VAR_APPRO, BSO_VAR_ACCUR];
    BSO_VAR_CAL_MMSE   = 1;     # use MMSE to estimate the variance
    BSO_VAR_CAL_MRC    = 2;     # use the MRC to estimate the variance
    BSO_VAR_CAL_ZF     = 3;     # use ZF to estimate the variance
    BSO_VAR_CAL_TYPES = [BSO_VAR_CAL_MMSE, BSO_VAR_CAL_MRC, BSO_VAR_CAL_ZF];
    # DSC
    # DSC - instantaneous square error
    DSC_ISE_NO      = 0;        # use the error directly
    DSC_ISE_MRC     = 1;        # in Alva's paper, he calls this matched filter
    DSC_ISE_ZF      = 2;
    DSC_ISE_MMSE    = 3;
    DSC_ISE_TYPES = [DSC_ISE_NO, DSC_ISE_MRC, DSC_ISE_ZF, DSC_ISE_MMSE];
    # DSC - mean previous source
    DSC_MEAN_PREV_SOUR_BSE = 1; # default in Alva's paper
    DSC_MEAN_PREV_SOUR_DSC = 2;
    DSC_MEAN_PREV_SOUR_TYPES = [DSC_MEAN_PREV_SOUR_BSE, DSC_MEAN_PREV_SOUR_DSC];
    # DSC - variance previous source
    DSC_VAR_PREV_SOUR_BSE = 1;  # default in Alva's paper
    DSC_VAR_PREV_SOUR_DSC = 2;
    DSC_VAR_PREV_SOUR_TYPES = [DSC_VAR_PREV_SOUR_BSE, DSC_VAR_PREV_SOUR_DSC];
    # Detect
    DETECT_SOUR_BSE = 1;
    DETECT_SOUR_DSC = 2;
    DETECT_SOURS = [DETECT_SOUR_BSE, DETECT_SOUR_DSC];
    # minimal value
    eps = 2.220446049250313e-16;
    # Batch size
    BATCH_SIZE_NO = None;
    
    # variables
    constellation = None;
    constellation_len = 0;
    bso_mean_init = None;
    bso_mean_cal = None;
    bso_var = None;
    bso_var_cal = None;
    dsc_ise = None;
    dsc_mean_prev_sour = None;
    dsc_var_prev_sour = None;
    min_var = None;
    iter_num = None;                # maximal iteration
    iter_diff_min = None;           # the minimal difference between 2 adjacent iterations
    detect_sour = None;
    
    '''
    init
    @constellation:         the constellation, a vector.
    @bso_mean_init:         1st iteration method in **BSO** to calculate the mean. Default: `BPIC.BSO_INIT_MMSE`, others: `BPIC.BSO_INIT_MRC, BPIC.BSO_INIT_ZF` (`BPIC.BSO_INIT_NO` should not be used but you can try)
    @bso_mean_cal:          other iteration method in **BSO** to calculate the mean. Default: `BPIC.BSO_MEAN_CAL_MRC` (`BPIC.BSO_MEAN_CAL_ZF` should not be used but you can try)
    @bso_var:               use approximate or accurate variance in **BSO**. Default: `BPIC.BSO_VAR_APPRO`, others: `BPIC.BSO_VAR_ACCUR`
    @bso_var_cal:           the method in **BSO** to calculate the variance. Default: `BPIC.BSO_VAR_CAL_MRC`, others: `BPIC.BSO_VAR_CAL_MRC` (`BSO_VAR_CAL_ZF` should not be used but you can try)
    @dsc_ise:               how to calculate the instantaneous square error. Default: `BPIC.DSC_ISE_MRC`, others: `BPIC.DSC_ISE_NO, BPIC.DSC_ISE_ZF, BPIC.DSC_ISE_MMSE`
    @dsc_mean_prev_sour:    the source of previous mean in DSC. Default: `BPIC.DSC_MEAN_PREV_SOUR_BSE`, others: `BPIC.DSC_MEAN_PREV_SOUR_DSC`
    @dsc_var_prev_sour:     the source of previous variance in DSC. Default: `BPIC.DSC_VAR_PREV_SOUR_BSE`, others: `BPIC.DSC_VAR_PREV_SOUR_DSC`
    @min_var:               the minimal variance.
    @iter_num:              the maximal iteration.
    @iter_diff_min:         the minimal difference in **DSC** to early stop.
    @detect_sour:           the source of detection result. Default: `BPIC.DETECT_SOUR_DSC`, others: `BPIC.DETECT_SOUR_BSE`.
    '''
    def __init__(self, constellation, *, bso_mean_init=BSO_MEAN_INIT_MMSE, bso_mean_cal=BSO_MEAN_CAL_MRC, bso_var=BSO_VAR_APPRO, bso_var_cal=BSO_VAR_CAL_MRC, dsc_ise=DSC_ISE_MRC, dsc_mean_prev_sour=DSC_MEAN_PREV_SOUR_BSE, dsc_var_prev_sour=DSC_VAR_PREV_SOUR_BSE, min_var=eps, iter_num=10, iter_diff_min=eps,detect_sour=DETECT_SOUR_DSC):
        constellation = np.asarray(constellation);
        if constellation.ndim != 1:
            raise Exception("The constellation must be a vector.");
        else:
            self.constellation = constellation;
            self.constellation_len = len(constellation);
        # other configurations
        if bso_mean_init not in BPIC.BSO_MEAN_INIT_TYPES:
            raise Exception("1st iteration method in BSO to calculate the mean is not recognised.");
        else:
            self.bso_mean_init = bso_mean_init;
        if bso_mean_cal not in BPIC.BSO_MEAN_CAL_TYPES:
            raise Exception("Other iteration method in BSO to calculate the mean is not recognised.");
        else:
            self.bso_mean_cal = bso_mean_cal;
        if bso_var not in BPIC.BSO_VAR_TYPES:
            raise Exception("Not set use whether approximate or accurate variance in BSO.");
        else:
            self.bso_var = bso_var;
        if bso_var_cal not in BPIC.BSO_VAR_CAL_TYPES:
            raise Exception("The method in BSO to calculate the variance is not recognised.");
        else:
            self.bso_var_cal = bso_var_cal;
        if dsc_ise not in BPIC.DSC_ISE_TYPES:
            raise Exception("How to calculate the instantaneous square error is not recognised.");
        else:
            self.dsc_ise = dsc_ise;
        if dsc_mean_prev_sour not in BPIC.DSC_MEAN_PREV_SOUR_TYPES:
            raise Exception("The source of previous mean in DSC is not recognised.");
        else:
            self.dsc_mean_prev_sour = dsc_mean_prev_sour;
        if dsc_var_prev_sour not in BPIC.DSC_VAR_PREV_SOUR_TYPES:
            raise Exception("The source of previous variance in DSC is not recognised.");
        else:
            self.dsc_var_prev_sour = dsc_var_prev_sour;
        self.min_var = min_var;
        self.iter_num = iter_num;
        if self.iter_num < 1:
            raise Exception("The iteration number must be positive.");
        self.iter_diff_min = iter_diff_min;
        if detect_sour not in BPIC.DETECT_SOURS:
            raise Exception("The source of detection result is not recognised.");
        else:
            self.detect_sour = detect_sour;
        self.batch_size = BPIC.BATCH_SIZE_NO;
    
    '''
    detect
    @y:       the received signal, [(batch_size), y]
    @H:       the channel matrix, [(batch_size), y_num, x_num]
    @No:      the noise (linear) power, [(batch_size), 1]
    '''
    def detect(self, y, H, No):
        # input check
        # input check - to numpy
        y = np.asarray(y);
        H = np.asarray(H);
        No = np.asarray(No);
        # input check - batch_size
        if y.ndim > 1 and y.shape[]:
            if y.shape[0] != H.shape[0] or y.shape[0] != H.shape[0]:
                raise Exception("The batch size (1st dimension) is not uniform for y, H and No.");
            else:
                self.batch_size = y.shape[0];
        # input check - dimension
        if self.batch_size == BPIC.BATCH_SIZE_NO and y.ndim !=1 or self.batch_size != BPIC.BATCH_SIZE_NO and y.ndim !=2:
            raise Exception("The received signal must be a vector.");
        if self.batch_size == BPIC.BATCH_SIZE_NO and H.ndim !=2 or self.batch_size != BPIC.BATCH_SIZE_NO and H.ndim !=3:
            raise Exception("The channel must be a matrix.");
        y_num = H.shape[-2];
        x_num = H.shape[-1];
        if y_num != y.shape[-1]:
            raise Exception("The channel row number does not equal to the signal number.");
        if y_num < x_num:
            raise Exception("The channel is a correlated channel.");
        if No.shape[-1] != 1 or self.batch_size == BPIC.BATCH_SIZE_NO and No.ndim !=1 or self.batch_size != BPIC.BATCH_SIZE_NO and No.ndim != 2:
            raise Exception("The noise power must be a scalar.");
            
        # constant values
        Ht = np.moveaxis(H, -1, -2);
        Hty = Ht @ y;
        HtH = Ht @ H;
        HtH_off = ((self.eye(x_num)+1) - self.eye(x_num)*2)*HtH;
        HtH_off_sqr = np.square(HtH_off);
        # constant values - inverse matrix
        mrc_mat = self.diag(1/self.diag(HtH));
        zf_mat = inv(HtH);
        # constant values - BSO - mean - 1st iter
        bso_zigma_1 = self.eye(x_num);
        if self.bso_mean_init == BPIC.BSO_MEAN_INIT_MMSE:
            bso_zigma_1 = inv(HtH + No*self.eye(x_num));
        if self.bso_mean_init == BPIC.BSO_MEAN_INIT_MRC:
            bso_zigma_1 = mrc_mat;
        if self.bso_mean_init == BPIC.BSO_MEAN_INIT_ZF:
            bso_zigma_1 = zf_mat;
        # constant values - BSO - mean - other iteration
        bso_zigma_others = mrc_mat;
        if self.bso_mean_cal == BPIC.BSO_MEAN_CAL_ZF:
            bso_zigma_others = zf_mat;
        # constant values - BSO - variance
        bso_var_mat = 1/self.diag(HtH);
        if self.bso_var_cal == BPIC.BSO_VAR_CAL_MMSE:
            bso_var_mat = self.diag(inv(HtH + No*self.eye(x_num)));
        if self.bso_var_cal == BPIC.BSO_VAR_CAL_ZF:
            bso_var_mat = self.diag(zf_mat);
        bso_var_mat_sqr = bso_var_mat**2;
        # constant values - DSC
        dsc_w = self.eye(x_num); # the default is `BPIC.DSC_ISE_NO`
        if self.dsc_ise == BPIC.DSC_ISE_MRC:
            dsc_w = mrc_mat;
        if self.dsc_ise == BPIC.DSC_ISE_ZF:
            dsc_w = zf_mat;
        if self.dsc_ise == BPIC.DSC_ISE_MMSE:
            dsc_w = inv(HtH + No*self.diag(self.ones(x_num, 1)));
        
        # iterative detection
        x_dsc = self.zeros(x_num);
        v_dsc = self.zeros(x_num);
        ise_dsc_prev = self.zeros(x_num);
        v_dsc_prev = None;
        x_bse_prev = None;
        v_bse_prev = None;
        for iter_id in range(self.iter_num):
            # BSO
            # BSO - mean
            if iter_id == 0:
                x_bso = bso_zigma_1@(Hty - HtH_off@x_dsc);
            else:
                x_bso = bso_zigma_others@(Hty - HtH_off@x_dsc);
                
            # BSO - variance
            if self.bso_var == BPIC.BSO_VAR_APPRO:
                v_bso = No*bso_var_mat;
            if self.bso_var == BPIC.BSO_VAR_ACCUR:
                v_bso = No*bso_var_mat + HtH_off_sqr@v_dsc*bso_var_mat_sqr;
            v_bso = np.clip(v_bso, self.min_var);
            
            # BSE
            # BSE - Estimate P(x|y) using Gaussian distribution
            pxyPdfExpPower = -1/v_bso*abs(self.repmat(x_bso, 1, self.constellation_len) - self.repmat(self.constellation, x_num, 1))**2;
            pxypdfExpNormPower = pxyPdfExpPower - np.expand_dims(pxyPdfExpPower.max(axix=-1), axis=-1);   # make every row the max power is 0
            pxyPdf = exp(pxypdfExpNormPower);
            # BSE - Calculate the coefficient of every possible x to make the sum of all
            pxyPdfCoeff = 1./np.sum(pxyPdf, axis=-1);
            pxyPdfCoeff = self.repmat(pxyPdfCoeff, 1, self.constellation_len);
            # BSE - PDF normalisation
            pxyPdfNorm = pxyPdfCoeff*pxyPdf;
            # BSE - calculate the mean and variance
            x_bse = np.sum(pxyPdfNorm*self.constellation, axis=-1);
            x_bse_mat = self.repmat(x_bse, 1, self.constellation_len);
            v_bse = np.sum(abs(x_bse_mat - self.constellation)**2*pxyPdfNorm, axis=-1);
            v_bse = np.clip(v_bse, self.min_var);
            
            # DSC
            # DSC - error
            ise_dsc = (dsc_w@(Hty - HtH@x_bse))**2;
            ies_dsc_sum = ise_dsc + ise_dsc_prev;
            ies_dsc_sum = np.clip(ies_dsc_sum, self.min_var);
            # DSC - rho (if we use this rho, we will have a little difference)
            rho_dsc = ise_dsc_prev/ies_dsc_sum;
            # DSC - mean
            if iter_id == 0:
                x_dsc = x_bse;
            else:
                if self.dsc_mean_prev_sour == BPIC.DSC_MEAN_PREV_SOUR_BSE:
                    #x_dsc = ise_dsc/ies_dsc_sum*x_bse_prev + ise_dsc_prev/ies_dsc_sum*x_bse;
                    x_dsc = (1 - rho_dsc)*x_bse_prev + rho_dsc*x_bse;
                if self.dsc_mean_prev_sour == BPIC.DSC_MEAN_PREV_SOUR_DSC:
                    x_dsc = (1 - rho_dsc)*x_dsc + rho_dsc*x_bse;
            # DSC - variance
            if iter_id == 0:
                v_dsc = v_bse;
            else:
                if self.dsc_var_prev_sour == BPIC.DSC_VAR_PREV_SOUR_BSE:
                    #v_dsc = ise_dsc./ies_dsc_sum.*v_bse_prev + ise_dsc_prev./ies_dsc_sum.*v_bse;
                    v_dsc = (1 - rho_dsc)*v_bse_prev + rho_dsc*v_bse;
                if self.dsc_var_prev_sour == BPIC.DSC_VAR_PREV_SOUR_DSC:
                    v_dsc = (1 - rho_dsc)*v_dsc + rho_dsc*v_bse;

            # early stop
            if iter_id > 0:
                if np.sum(abs(v_dsc - v_dsc_prev)**2) <= self.iter_diff_min:
                    break;
            
            # update statistics
            # update statistics - BSE
            if self.dsc_mean_prev_sour == BPIC.DSC_MEAN_PREV_SOUR_BSE:
                x_bse_prev = x_bse;
            if self.dsc_var_prev_sour == BPIC.DSC_VAR_PREV_SOUR_BSE:
                v_bse_prev = v_bse;
            # update statistics - DSC
            v_dsc_prev = v_dsc;
            # update statistics - DSC - instantaneous square error
            ise_dsc_prev = ise_dsc;
        # take the detection value
        if self.detect_sour == BPIC.DETECT_SOUR_BSE:
            return x_bse;
        if self.detect_sour == BPIC.DETECT_SOUR_DSC:
            return x_dsc;
        
    ##########################################################################
    # Functions uniform with non-batch and batch
    ##########################################################################
    def eye(self, size):
        out = np.eye(size);
        if self.batch_size is not BPIC.BATCH_SIZE_NO:
            out = np.tile(out,(self.batch_size, 1, 1));
            return out;
    
    '''
    generate a matrix of all zeros
    @order: 'C': this function only create given dimensions; 'F': create the dimensions as matlab (2D at least)
    '''
    def zeros(self, nrow, *args, order='C'):
        out = None;
        if order == 'F':
            ncol = nrow;
            if len(args) >= 1:
                ncol = args[0];
            out = np.zeros((nrow, ncol)) if self.batch_size == BPIC.BATCH_SIZE_NO else np.zeros((self.batch_size, nrow, ncol));
        elif order == 'C':
            zeros_shape = list(args);
            zeros_shape.insert(0, nrow);
            if self.batch_size != BPIC.BATCH_SIZE_NO:
                zeros_shape.insert(0, self.batch_size);
            out = np.zeros(zeros_shape);
        return out;
    
    
    '''
    generate a matrix based on its diag or get a diagonal matrix from its vector
    '''
    def diag(self, diag_vec):
        out = None;
        diag_vec_len = diag_vec.shape[-1];
        if self.batch_size is BPIC.BATCH_SIZE_NO:
            out = np.diag(diag_vec);
        else:
            # np.zeros only take real numbers by default, here we need to put complex value into it
            out = [];
            # create output
            for batch_id in range(self.batch_size):
                out[batch_id] = np.diag(diag_vec[batch_id, ...]);
            out = np.asarray(out);
        return out;
    
    '''
    repeat the matrix in the given dimension (as matlab)
    '''
    def repmat(self, mat, nrow, *args):
        out = None;
        ncol = args[0] if len(args) >= 1 else nrow;
        out = np.tile(mat, (nrow, ncol)) if self.batch_size == BPIC.BATCH_SIZE_NO else np.tile(mat, (1, nrow, ncol));