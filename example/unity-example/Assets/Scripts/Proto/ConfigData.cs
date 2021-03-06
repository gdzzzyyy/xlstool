/*
* @file: ConfigData.cs
* @brief: This file is generated by xlstool, please don't edit it.
*/

using System;
using System.Collections.Generic;

namespace MyGame {
    public static class ConfigData {
#region DataBlocks
        private static ConfigDataStorage _dataBlocks;
        private static readonly Dictionary<int, Goods> _GoodsItems = new Dictionary<int, Goods>();
        private static readonly Dictionary<int, Skill> _SkillItems = new Dictionary<int, Skill>();
#endregion

        public static bool Init(byte[] bytes) {
            _dataBlocks = ConfigDataStorage.Parser.ParseFrom(bytes);
            if (_dataBlocks == null) return false;
            for (int i = 0; i < _dataBlocks.GoodsItems.Count; ++i) {
                var item = _dataBlocks.GoodsItems[i];
                _GoodsItems[item.Id] = item;
            }
            for (int i = 0; i < _dataBlocks.SkillItems.Count; ++i) {
                var item = _dataBlocks.SkillItems[i];
                _SkillItems[item.Id] = item;
            }
            return true;
        }

        public static int GoodsCount() {
            return _dataBlocks.GoodsItems.Count;
        }

        public static Goods GoodsItem(int index) {
            return _dataBlocks.GoodsItems[index];
        }

        public static Goods GoodsFind(int id) {
            Goods item;
            _GoodsItems.TryGetValue(id, out item);
            return item;
        }

        public static int SkillCount() {
            return _dataBlocks.SkillItems.Count;
        }

        public static Skill SkillItem(int index) {
            return _dataBlocks.SkillItems[index];
        }

        public static Skill SkillFind(int id) {
            Skill item;
            _SkillItems.TryGetValue(id, out item);
            return item;
        }


    }  // ConfigData
}  // MyGame
