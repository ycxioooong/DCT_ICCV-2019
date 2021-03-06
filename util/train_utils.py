
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import os.path as osp
import sys
import shutil
import time
from datetime import datetime


class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


class LossStat(object):
    def __init__(self, num_data):
        self.total_losses = AverageMeter()
        self.joints2d_losses = AverageMeter()
        self.dp_align_losses = AverageMeter()
        self.joints3d_losses = AverageMeter()
        self.smpl_joints_losses = AverageMeter()
        self.smpl_params_losses = AverageMeter()
        self.num_data = num_data
        self.has_dp_loss = False
        self.has_smpl_joints_loss = False
        self.has_smpl_param_loss = False
    
    def set_epoch(self, epoch):
        self.epoch = epoch
    
    def update(self, errors):
        self.total_losses.update(errors['total_loss'])
        self.joints2d_losses.update(errors['kp_loss'])
        if 'dp_align_loss' in errors:
            self.dp_align_losses.update(errors['dp_align_loss'])
            self.has_dp_loss = True
        if 'smpl_joints_loss' in errors:
            self.smpl_joints_losses.update(errors['smpl_joints_loss'])
            self.has_smpl_joints_loss = True
        if 'smpl_params_loss' in errors:
            self.smpl_params_losses.update(errors['smpl_params_loss'])
            self.has_smpl_param_loss = True
    
    def print_loss(self, epoch_iter):
        print_content = 'Epoch:[{}][{}/{}]\t' + \
                                    'Total Loss {tot_loss.val:.4f}({tot_loss.avg:.4f})\t' + \
                                    'Joints 2D Loss {kp_loss.val:.4f}({kp_loss.avg:.4f})\t'
        print_content = print_content.format(self.epoch, epoch_iter, self.num_data,
                        tot_loss = self.total_losses, kp_loss = self.joints2d_losses)

        if self.has_dp_loss:
            print_content += '\nEpoch:[{}][{}/{}]\t' + \
                            'Densepose Align Loss {dp_align_loss.val:.4f}({dp_align_loss.avg:.4f})\t'
            print_content = print_content.format(self.epoch, epoch_iter, self.num_data,
                                                dp_align_loss = self.dp_align_losses)

        if self.has_smpl_joints_loss:
            print_content += '\nEpoch:[{}][{}/{}]\t' + \
                'SMPL joints Loss {joints3d_loss.val:.4f}({joints3d_loss.avg:.4f})\t'
            print_content = print_content.format( self.epoch, epoch_iter, self.num_data,
                    joints3d_loss = self.smpl_joints_losses)

        if self.has_smpl_param_loss:
            print_content += '\nEpoch:[{}][{}/{}]\t' + \
                'SMPL Params Loss {smpl_params_loss.val:.4f}({smpl_params_loss.avg:.4f})\t'
            print_content = print_content.format(self.epoch, epoch_iter, self.num_data,
                    smpl_params_loss = self.smpl_params_losses)
        print(print_content)


class TimeStat(object):
    def __init__(self, total_epoch=100):
        self.data_time = AverageMeter()
        self.forward_time = AverageMeter()
        self.visualize_time = AverageMeter()
        self.total_time = AverageMeter()
        self.total_epoch = total_epoch
    
    def epoch_init(self, epoch):
        self.data_time_epoch = 0.0
        self.forward_time_epoch = 0.0
        self.visualize_time_epoch = 0.0
        self.start_time = time.time()
        self.epoch_start_time = time.time()
        self.forward_start_time = -1
        self.visualize_start_time = -1
        self.epoch = epoch
    
    def stat_data_time(self):
        self.forward_start_time = time.time()
        self.data_time_epoch += (self.forward_start_time - self.start_time)

    def stat_forward_time(self):
        self.visualize_start_time = time.time()
        self.forward_time_epoch += (self.visualize_start_time - self.forward_start_time)
    
    def stat_visualize_time(self):
        visualize_end_time = time.time()
        self.start_time = visualize_end_time
        self.visualize_time_epoch += visualize_end_time - self.visualize_start_time
    
    def stat_epoch_time(self):
        epoch_end_time = time.time()
        self.epoch_time = epoch_end_time - self.epoch_start_time
    
    def print_stat(self):
        self.data_time.update(self.data_time_epoch)
        self.forward_time.update(self.forward_time_epoch)
        self.visualize_time.update(self.visualize_time_epoch)

        time_content = f"End of epoch {self.epoch} / {self.total_epoch} \t" \
                        f"Time Taken: data {self.data_time.avg:.2f}, " \
                        f"forward {self.forward_time.avg:.2f}, " \
                        f"visualize {self.visualize_time.avg:.2f}, " \
                        f"Total {self.epoch_time:.2f} \n" 
        time_content += f"Epoch {self.epoch} compeletes in {datetime.now().strftime('%Y-%m-%d:%H:%M:%S')}"
        print(time_content)