#!/usr/bin/env python
# -*- coding: utf-8 -*-

import six
import numpy as np
import nibabel as nb
import pandas as pd
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces.base import BaseInterface, \
    BaseInterfaceInputSpec, traits, File, TraitedSpec

from sklearn import metrics
from sklearn.preprocessing import LabelEncoder


def serialize_parameters(parameters):
    return '; '.join(
        '%s: %s' % (k, parameters[k])
        for k in sorted(parameters.keys())
    )

class ReportInputSpec(TraitedSpec):
    X_train = traits.Any(mandatory=True)
    y_train = traits.Any(mandatory=True)
    X_valid = traits.Any(mandatory=True)
    y_valid = traits.Any(mandatory=True)

    fold = traits.Any(mandatory=True)
    config = traits.Any(mandatory=True)

    label_encoder = traits.Instance(klass=LabelEncoder)


class ReportOutputSpec(TraitedSpec):
    report = File(desc="CSV report with all the combinations"
                       " and cross-validation folds",
                  exists=True, mandatory=True)


class ReportInterface(BaseInterface):
    input_spec = ReportInputSpec
    output_spec = ReportOutputSpec

    def _run_interface(self, runtime):
        from nipype import logging
        logger = logging.getLogger('interface')

        combinations = zip(self.inputs.X_train, self.inputs.y_train,
                          self.inputs.X_valid, self.inputs.y_valid,
                          self.inputs.fold, self.inputs.config)

        rows = []

        for X_train, y_train, X_valid, y_valid, fold, config in combinations:
            row = {
                'fold': fold
            }

            if self.inputs.label_encoder:
                le = self.inputs.label_encoder
                if len(le.classes_) == 2:
                    row['train tn'], \
                    row['train fp'], \
                    row['train fn'], \
                    row['train tp'] = metrics.confusion_matrix(np.round(y_train), np.round(X_train)).ravel()

                    row['valid tn'], \
                    row['valid fp'], \
                    row['valid fn'], \
                    row['valid tp'] = metrics.confusion_matrix(np.round(y_valid), np.round(X_valid)).ravel()

            row['train roc auc'] = metrics.roc_auc_score(y_train, X_train)
            row['valid roc auc'] = metrics.roc_auc_score(y_valid, X_valid)
                
            row['roi'] = config['roi']['type']
            row['roi parameters'] = \
                ' ' if not config['roi']['parameters'] \
                else serialize_parameters(config['roi']['parameters'])

            row['connectivity'] = config['connectivity']['type']
            row['connectivity parameters'] = \
                ' ' if not config['connectivity']['parameters'] \
                else serialize_parameters(config['connectivity']['parameters'])
                

            row['classifier'] = config['classifier']['type']
            row['classifier parameters'] = \
                ' ' if not config['classifier']['parameters'] \
                else serialize_parameters(config['classifier']['parameters'])

            rows += [row]

        self._df = pd.DataFrame(rows)
                
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['report'] = './connectome_report.csv'

        cols_order = [
            'roi', 'roi parameters',
            'connectivity', 'connectivity parameters',
            'classifier', 'classifier parameters',
            'fold',
            'train roc auc',
            'valid roc auc',
        ]

        if self.inputs.label_encoder:
            le = self.inputs.label_encoder
            if len(le.classes_) == 2:
                cols_order += [
                    'train tp',
                    'train tn',
                    'train fp',
                    'train fn',
                    'valid tp',
                    'valid tn',
                    'valid fp',
                    'valid fn',
                ]

        self._df.to_csv('./connectome_report.csv', cols=cols_order, index=False)

        return outputs

