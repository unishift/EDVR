import os.path as osp
import torch
import torch.utils.data as data
import data.util as util


class VideoTestDataset(data.Dataset):
    """
    A video test dataset. Support:
    Vid4
    REDS4
    Vimeo90K-Test

    no need to prepare LMDB files
    """

    def __init__(self, opt):
        super(VideoTestDataset, self).__init__()
        self.current_folder = None
        self.img_buf = None
        self.opt = opt
        self.cache_data = opt['cache_data']
        self.half_N_frames = opt['N_frames'] // 2
        self.GT_root, self.LQ_root = opt['dataroot_GT'], opt['dataroot_LQ']
        self.data_type = self.opt['data_type']
        self.data_info = {'path_LQ': [], 'path_GT': [], 'folder': [], 'idx': [], 'border': []}
        if self.data_type == 'lmdb':
            raise ValueError('No need to use LMDB during validation/test.')
        #### Generate data info and cache data
        self.imgs_LQ, self.imgs_GT = {}, {}

        self.need_GT = self.GT_root is not None
        if self.need_GT:
            subfolders_LQ = util.glob_file_list(self.LQ_root)
            subfolders_GT = util.glob_file_list(self.GT_root)
            for subfolder_LQ, subfolder_GT in zip(subfolders_LQ, subfolders_GT):
                subfolder_name = osp.basename(subfolder_GT)
                img_paths_LQ = util.glob_file_list(subfolder_LQ)
                img_paths_GT = util.glob_file_list(subfolder_GT)
                max_idx = len(img_paths_LQ)
                assert max_idx == len(
                    img_paths_GT), 'Different number of images in LQ and GT folders'
                self.data_info['path_LQ'].extend(img_paths_LQ)
                self.data_info['path_GT'].extend(img_paths_GT)
                self.data_info['folder'].extend([subfolder_name] * max_idx)
                for i in range(max_idx):
                    self.data_info['idx'].append('{}/{}'.format(i, max_idx))
                border_l = [0] * max_idx
                for i in range(self.half_N_frames):
                    border_l[i] = 1
                    border_l[max_idx - i - 1] = 1
                self.data_info['border'].extend(border_l)

                if self.cache_data:
                    self.imgs_LQ[subfolder_name] = util.read_img_seq(img_paths_LQ, 16)
                    self.imgs_GT[subfolder_name] = util.read_img_seq(img_paths_GT, 16)
        else:
            subfolders_LQ = util.glob_file_list(self.LQ_root)
            for subfolder_LQ in subfolders_LQ:
                subfolder_name = osp.basename(subfolder_LQ)
                img_paths_LQ = util.glob_file_list(subfolder_LQ)
                max_idx = len(img_paths_LQ)

                self.data_info['path_LQ'].extend(img_paths_LQ)
                self.data_info['folder'].extend([subfolder_name] * max_idx)
                for i in range(max_idx):
                    self.data_info['idx'].append('{}/{}'.format(i, max_idx))
                border_l = [0] * max_idx
                for i in range(self.half_N_frames):
                    border_l[i] = 1
                    border_l[max_idx - i - 1] = 1
                self.data_info['border'].extend(border_l)

                if self.cache_data:
                    self.imgs_LQ[subfolder_name] = util.read_img_seq(img_paths_LQ, 16)

    def __getitem__(self, index):
        path_LQ = self.data_info['path_LQ'][index]
        path_GT = self.data_info['path_GT'][index] if self.need_GT else None
        folder = self.data_info['folder'][index]
        idx, max_idx = self.data_info['idx'][index].split('/')
        idx, max_idx = int(idx), int(max_idx)
        border = self.data_info['border'][index]

        if self.cache_data:
            select_idx = util.index_generation(idx, max_idx, self.opt['N_frames'],
                                               padding=self.opt['padding'])
            imgs_LQ = self.imgs_LQ[folder].index_select(0, torch.LongTensor(select_idx))
            img_GT = self.imgs_GT[folder][idx] if self.need_GT else None
        else:
            if self.current_folder is None or self.current_folder != folder:
                self.current_folder = folder
                img_paths_LQ = [self.data_info['path_LQ'][i] for i in range(index, index + max_idx)
                                                                if self.data_info['folder'][i] == folder]
                self.img_buf = {'LQ': util.read_img_seq(img_paths_LQ, 16)}

                if self.need_GT:
                    img_paths_GT = [self.data_info['path_GT'][i] for i in range(index, index + max_idx)
                                                                    if self.data_info['folder'][i] == folder]
                    self.img_buf['GT'] = util.read_img_seq(img_paths_GT, 16)


            select_idx = util.index_generation(idx, max_idx, self.opt['N_frames'],
                                               padding=self.opt['padding'])
            imgs_LQ = self.img_buf['LQ'].index_select(0, torch.LongTensor(select_idx))
            img_GT = self.img_buf['GT'][idx] if self.need_GT else None


        if self.need_GT:
            return {
                'LQs': imgs_LQ,
                'GT': img_GT,
                'folder': folder,
                'idx': self.data_info['idx'][index],
                'border': border,
                'LQ_path': path_LQ,
                'GT_path': path_GT,
            }
        else:
            return {
                'LQs': imgs_LQ,
                'folder': folder,
                'idx': self.data_info['idx'][index],
                'border': border,
                'LQ_path': path_LQ,
            }

    def __len__(self):
        return len(self.data_info['path_LQ'])
