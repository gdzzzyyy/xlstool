/*
 * File Name: main.cc
 * Author: Stan.Lch
 * Mail: fn.stanc@gmail.com
 * Created Time: 2018/7/21 13:21:24
 */

 #include "ConfigData.h"
 #include <fstream>
 #include <iostream>

using namespace MyGame;
int main(int argc, char *argv[])
{
    std::ifstream in(argv[1], std::ios::binary);
    std::string bytes((std::istreambuf_iterator<char>(in)),
                     std::istreambuf_iterator<char>());
    ConfigData config_data;
    if (!config_data.init(bytes)) {
        std::cerr << "ConfigData::Init error." << std::endl;
        return 0;
    }

    auto goods = config_data.getGoods(3403);
    if (goods) {
        std::cout << goods->DebugString() << std::endl;
    }

    return 0;
}
