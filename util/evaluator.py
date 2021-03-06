from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import shutil
import os.path as osp
import numpy as np
import pickle
import copy
import cv2
import time
import util.parallel_io as pio
import util.ry_utils as ry_utils
import data.data_utils as data_utils
import util.eval_utils as eval_utils
import multiprocessing as mp


class Evaluator(object):

    def __init__(self, data_list=None):
        if data_list is not None:
            self.data_list = copy.deepcopy(data_list)
        self.pred_results = list()

    def clear(self):
        self.pred_results = list()

    def update(self, data_idxs, pred_results):
        for i, data_idx in enumerate(data_idxs):
            single_data = dict(
                data_idx=data_idx,
                cam=pred_results['cams'][i],
                smpl_shape=pred_results['shape_params'][i],
                smpl_pose=pred_results['pose_params'][i],
                pred_verts=pred_results['pred_verts'][i].astype(np.float16)
            )
            self.pred_results.append(single_data)

    def remove_redunc(self):
        new_pred_results = list()
        img_id_set = set()
        for data in self.pred_results:
            data_idx = data['data_idx']
            img_path = eval_utils.get_img_path(self.data_list[data_idx])
            img_id = img_path
            if img_id not in img_id_set:
                new_pred_results.append(data)
                img_id_set.add(img_id)
        self.pred_results = new_pred_results
        print("Number of test data:", len(self.pred_results))


    def build_dirs(self):
        for i, result in enumerate(self.pred_results):
            img_path = eval_utils.get_img_path(self.data_list[result['data_idx']])
            img = eval_utils.pad_and_resize(cv2.imread(img_path))
            subdir = eval_utils.get_subdir(img_path)
            res_subdir = osp.join(res_dir, subdir)
            if not osp.exists(res_subdir):
                os.makedirs(res_subdir)

    def visualize_result_single(self, start, end, smpl):
        import util.render_util as render_util
        for i, result in enumerate(self.pred_results[start:end]):
            img_path = eval_utils.get_img_path(self.data_list[result['data_idx']])
            img = eval_utils.pad_and_resize(cv2.imread(img_path))
            img_name = img_path.split('/')[-1]
            subdir = eval_utils.get_subdir(img_path)
            res_subdir = osp.join(res_dir, subdir)
            res_img_path = osp.join(res_subdir, img_name)
            render_img = render_util.render_smpl_to_image(
                img.copy(), result['pred_verts'], result['cam'], self.renderer)
            render_img = np.concatenate((img, render_img), axis=1)
            blank_img = np.ones((224,224,3),dtype=np.uint8)
            render_img = np.concatenate((render_img, blank_img), axis=1)
            render_pred_smpl = render_util.render_image(result['smpl_pose'], result['smpl_shape'], smpl)
            res_img = np.concatenate((render_img, render_pred_smpl), axis=0)
            cv2.imwrite(res_img_path, res_img)
            if i%10 == 0:
                print("{} Processed:{}/{}".format(os.getpid(), i, len(self.pred_results[start:end])))

    def visualize_result(self, model_dir, res_dir):
        assert sys.version_info[0] == 2, "This code could only run in Python 2"
        from models.renderer import SMPLRenderer
        from smpl_webuser.serialization import load_model

        smpl_model_path = osp.join(model_dir, 'smpl_cocoplus_neutral.pkl')
        self.renderer = SMPLRenderer(
            img_size=224, face_path=osp.join(model_dir, 'smpl_faces.npy'))
        # build result subdirs first
        self.build_dirs()
        # start processing
        num_process = min(8, len(self.pred_results))
        num_each = len(self.pred_results) // num_process
        process_list = list()
        for i in range(num_process):
            start = i*num_each
            end = (i+1)*num_each if i<num_process-1 else len(self.pred_results)
            smpl = load_model(smpl_model_path)
            p = mp.Process(target=self.visualize_result_single, args=(start, end, smpl))
            p.start()
            process_list.append(p)
        for p in process_list:
            p.join()


    def save_to_pkl(self, res_pkl_file):
        saved_data = dict(
            data_list=self.data_list,
            pred_results=self.pred_results
        )
        pio.save_pkl_single(res_pkl_file, saved_data, protocol=2)

    def load_from_pkl(self, pkl_path):
        saved_data = pio.load_pkl_single(pkl_path)
        self.data_list = saved_data['data_list']
        self.pred_results = saved_data['pred_results']


if __name__ == '__main__':
    evaluator = Evaluator()
    model_dir = sys.argv[1]
    pkl_path = 'evaluate_results/eval_result.pkl'
    res_dir = 'evaluate_results/images'
    ry_utils.renew_dir(res_dir)
    evaluator.load_from_pkl(pkl_path)
    evaluator.visualize_result(model_dir, res_dir)