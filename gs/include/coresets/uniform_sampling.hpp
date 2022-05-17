#pragma once

#include <algorithm>
#include <vector>
#include <iostream>

#include <coresets/coreset.hpp>
#include <utils/random.hpp>

namespace coresets
{
    class UniformSampling
    {
    public:
        /**
         * Number of points that the algorithm should aim to include in the coreset: T
         */
        const size_t TargetSamplesInCoreset;

        UniformSampling(size_t targetSamplesInCoreset);

        std::shared_ptr<Coreset>
        run(const blaze::DynamicMatrix<double> &data);

    private:
        utils::Random random;
    };
}
